import json
import subprocess
import sys
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


class TestAnalyzeCLI:
    def test_cli_writes_results_json(self, collected_dir, tmp_path):
        results_dir = tmp_path / "results"
        result = subprocess.run(
            [sys.executable, "-m", "wxcli.org_health.analyze",
             str(collected_dir), "--output", str(results_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert (results_dir / "results.json").exists()
        data = json.loads((results_dir / "results.json").read_text())
        assert data["org_name"] == "Acme Corp"
        assert "findings" in data
        assert "categories" in data

    def test_cli_missing_manifest_exits_1(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        results_dir = tmp_path / "results"
        result = subprocess.run(
            [sys.executable, "-m", "wxcli.org_health.analyze",
             str(empty_dir), "--output", str(results_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "manifest" in result.stderr.lower()

    def test_cli_creates_output_dir(self, collected_dir, tmp_path):
        results_dir = tmp_path / "deeply" / "nested" / "results"
        result = subprocess.run(
            [sys.executable, "-m", "wxcli.org_health.analyze",
             str(collected_dir), "--output", str(results_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert results_dir.exists()


class TestEdgeCases:
    def test_empty_org_no_crash(self, collected_dir):
        """An org with all empty lists should produce zero findings, not crash."""
        result = run_analysis(collected_dir)
        assert len(result.findings) == 0
        assert result.stats.total_users == 0
        assert result.stats.total_devices == 0

    def test_mixed_findings_across_categories(self, collected_dir):
        """Multiple issues across categories all appear in results."""
        aa_data = [{"id": "aa-1", "name": "Disabled", "locationName": "HQ", "enabled": False}]
        trunk_data = [{"id": "t-1", "name": "Bad Trunk", "trunkType": "REGISTERING",
                       "inUse": True, "registrationStatus": "error"}]
        device_data = [{"id": "d-1", "displayName": "Offline", "connectionStatus": "disconnected",
                        "product": "Cisco 8845"}]
        (collected_dir / "auto_attendants.json").write_text(json.dumps(aa_data))
        (collected_dir / "trunks.json").write_text(json.dumps(trunk_data))
        (collected_dir / "devices.json").write_text(json.dumps(device_data))
        result = run_analysis(collected_dir)
        categories_with_findings = [
            k for k, v in result.categories.items()
            if v.high_count + v.medium_count + v.low_count + v.info_count > 0
        ]
        assert len(categories_with_findings) == 3

    def test_location_count_derived_from_data(self, collected_dir):
        users = [
            {"id": "u-1", "displayName": "User 1", "locationName": "Dallas"},
            {"id": "u-2", "displayName": "User 2", "locationName": "Austin"},
            {"id": "u-3", "displayName": "User 3", "locationName": "Dallas"},
        ]
        (collected_dir / "users.json").write_text(json.dumps(users))
        result = run_analysis(collected_dir)
        assert result.stats.total_locations == 2
