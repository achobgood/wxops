import json
from wxcli.org_health.models import Finding, CategoryScore, HealthResult, OrgStats


class TestFinding:
    def test_construction(self):
        f = Finding(
            check_name="disabled_auto_attendant",
            category="feature_utilization",
            severity="MEDIUM",
            title="3 Auto Attendants are disabled",
            detail="Disabled auto attendants consume configuration space without serving callers.",
            affected_items=[{"id": "aa-1", "name": "Main AA", "location": "HQ"}],
            recommendation="Enable or delete these auto attendants.",
        )
        assert f.check_name == "disabled_auto_attendant"
        assert f.severity == "MEDIUM"
        assert len(f.affected_items) == 1

    def test_finding_to_dict(self):
        f = Finding(
            check_name="test",
            category="security",
            severity="HIGH",
            title="Test finding",
            detail="Detail text",
            affected_items=[],
            recommendation="Fix it.",
        )
        d = f.to_dict()
        assert d["check_name"] == "test"
        assert d["severity"] == "HIGH"
        assert isinstance(d["affected_items"], list)


class TestCategoryScore:
    def test_construction_and_counts(self):
        findings = [
            Finding("c1", "security", "HIGH", "t1", "d1", [], "r1"),
            Finding("c2", "security", "MEDIUM", "t2", "d2", [], "r2"),
            Finding("c3", "security", "HIGH", "t3", "d3", [], "r3"),
        ]
        cs = CategoryScore.from_findings("security", "Security Posture", findings)
        assert cs.high_count == 2
        assert cs.medium_count == 1
        assert cs.low_count == 0
        assert cs.info_count == 0
        assert len(cs.findings) == 3


class TestOrgStats:
    def test_construction(self):
        stats = OrgStats(
            total_users=100,
            total_devices=150,
            total_auto_attendants=5,
            total_call_queues=3,
            total_hunt_groups=2,
            total_trunks=4,
            total_locations=3,
            sampled_users_for_permissions=50,
        )
        assert stats.total_users == 100
        assert stats.total_locations == 3


class TestHealthResult:
    def test_serialization_round_trip(self):
        finding = Finding("c1", "security", "HIGH", "t", "d", [{"id": "x"}], "r")
        cat = CategoryScore.from_findings("security", "Security Posture", [finding])
        stats = OrgStats(10, 20, 1, 1, 1, 1, 2, 10)
        result = HealthResult(
            org_name="Test Org",
            org_id="org-123",
            collected_at="2026-04-17T14:30:00Z",
            categories={"security": cat},
            findings=[finding],
            stats=stats,
        )
        serialized = json.dumps(result.to_dict())
        loaded = json.loads(serialized)
        assert loaded["org_name"] == "Test Org"
        assert len(loaded["findings"]) == 1
        assert loaded["categories"]["security"]["high_count"] == 1
