import json
import subprocess
import sys
import pytest
from pathlib import Path

from wxcli.org_health.analyze import run_analysis
from wxcli.org_health.models import HealthResult


CATEGORY_DISPLAY_NAMES = {
    "feature_utilization": "Feature Utilization",
    "device_health": "Device Health",
    "security": "Security Posture",
    "routing": "Routing Hygiene",
}


class TestRunAnalysis:
    def test_clean_org_produces_zero_findings(self, collected_dir):
        result = run_analysis(collected_dir)
        assert isinstance(result, HealthResult)
        assert len(result.findings) == 0
        assert result.org_name == "Acme Corp"
        assert result.org_id == "org-abc-123"

    def test_all_four_categories_present(self, collected_dir):
        result = run_analysis(collected_dir)
        for cat_key in CATEGORY_DISPLAY_NAMES:
            assert cat_key in result.categories
            assert result.categories[cat_key].display_name == CATEGORY_DISPLAY_NAMES[cat_key]

    def test_findings_appear_in_result(self, collected_dir):
        aa_data = [
            {"id": "aa-1", "name": "Disabled AA", "locationName": "HQ", "enabled": False},
        ]
        (collected_dir / "auto_attendants.json").write_text(json.dumps(aa_data))
        result = run_analysis(collected_dir)
        assert len(result.findings) >= 1
        disabled = [f for f in result.findings if f.check_name == "disabled_auto_attendants"]
        assert len(disabled) == 1
        assert result.categories["feature_utilization"].medium_count >= 1

    def test_org_stats_populated(self, collected_dir):
        users = [{"id": f"u-{i}", "displayName": f"User {i}"} for i in range(10)]
        devices = [
            {"id": f"d-{i}", "displayName": f"Phone {i}", "connectionStatus": "connected",
             "product": "Cisco 8845", "personId": f"u-{i}"}
            for i in range(8)
        ]
        (collected_dir / "users.json").write_text(json.dumps(users))
        (collected_dir / "devices.json").write_text(json.dumps(devices))
        result = run_analysis(collected_dir)
        assert result.stats.total_users == 10
        assert result.stats.total_devices == 8

    def test_result_serializes_to_json(self, collected_dir):
        result = run_analysis(collected_dir)
        serialized = json.dumps(result.to_dict(), indent=2)
        loaded = json.loads(serialized)
        assert loaded["org_name"] == "Acme Corp"
        assert "categories" in loaded
        assert "findings" in loaded
        assert "stats" in loaded
