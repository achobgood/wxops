# tests/org_health/test_report.py
import json
import subprocess
import sys
import pytest
from pathlib import Path

from wxcli.org_health.models import Finding, CategoryScore, HealthResult, OrgStats
from wxcli.org_health.report import generate_report


@pytest.fixture
def sample_result():
    findings = [
        Finding("disabled_auto_attendants", "feature_utilization", "MEDIUM",
                "2 Auto Attendants are disabled",
                "Disabled AAs consume config space.",
                [{"id": "aa-1", "name": "Old AA", "location": "HQ"},
                 {"id": "aa-2", "name": "Test AA", "location": "Branch"}],
                "Enable or delete these auto attendants."),
        Finding("trunk_errors", "routing", "HIGH",
                "1 trunk is not registered",
                "Trunk in error state.",
                [{"id": "t-1", "name": "Dallas LGW", "type": "REGISTERING", "status": "error"}],
                "Investigate gateway connectivity."),
        Finding("offline_devices", "device_health", "HIGH",
                "3 devices are offline",
                "Offline devices cannot make calls.",
                [{"id": "d-1", "name": "Lobby", "product": "8845", "status": "disconnected"},
                 {"id": "d-2", "name": "Conf", "product": "8865", "status": "offline"},
                 {"id": "d-3", "name": "Exec", "product": "9871", "status": "disconnected"}],
                "Investigate connectivity."),
    ]
    categories = {}
    for cat_key, display in [
        ("security", "Security Posture"),
        ("routing", "Routing Hygiene"),
        ("feature_utilization", "Feature Utilization"),
        ("device_health", "Device Health"),
    ]:
        cat_findings = [f for f in findings if f.category == cat_key]
        categories[cat_key] = CategoryScore.from_findings(cat_key, display, cat_findings)

    stats = OrgStats(
        total_users=277, total_devices=340, total_auto_attendants=8,
        total_call_queues=5, total_hunt_groups=3, total_trunks=4,
        total_locations=6, sampled_users_for_permissions=50,
    )
    return HealthResult(
        org_name="Acme Corp",
        org_id="org-abc-123",
        collected_at="2026-04-17T14:30:00Z",
        categories=categories,
        findings=findings,
        stats=stats,
    )


@pytest.fixture
def zero_findings_result():
    categories = {}
    for cat_key, display in [
        ("security", "Security Posture"),
        ("routing", "Routing Hygiene"),
        ("feature_utilization", "Feature Utilization"),
        ("device_health", "Device Health"),
    ]:
        categories[cat_key] = CategoryScore.from_findings(cat_key, display, [])
    stats = OrgStats(50, 60, 2, 1, 1, 2, 3, 50)
    return HealthResult(
        org_name="Clean Org",
        org_id="org-clean",
        collected_at="2026-04-17T14:30:00Z",
        categories=categories,
        findings=[],
        stats=stats,
    )


class TestGenerateReport:
    def test_returns_html_string(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="Adam Hobgood")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_brand_and_prepared_by_in_header(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="Adam Hobgood")
        assert "Acme Corp" in html
        assert "Adam Hobgood" in html

    def test_all_four_categories_rendered(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="SE")
        assert "Security Posture" in html
        assert "Routing Hygiene" in html
        assert "Feature Utilization" in html
        assert "Device Health" in html

    def test_findings_rendered_with_severity(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="SE")
        assert "2 Auto Attendants are disabled" in html
        assert "1 trunk is not registered" in html
        assert "3 devices are offline" in html

    def test_stat_cards_present(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="SE")
        assert "277" in html  # total users
        assert "340" in html  # total devices

    def test_zero_findings_shows_checkmark(self, zero_findings_result):
        html = generate_report(zero_findings_result, brand="Clean Org", prepared_by="SE")
        assert "No issues found" in html or "✓" in html or "checkmark" in html.lower()

    def test_affected_items_table(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="SE")
        assert "Dallas LGW" in html
        assert "Old AA" in html

    def test_recommendation_rendered(self, sample_result):
        html = generate_report(sample_result, brand="Acme Corp", prepared_by="SE")
        assert "Enable or delete" in html
        assert "Investigate gateway" in html
