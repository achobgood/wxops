import json
import pytest
from wxcli.org_health.collector import load_manifest, load_collected_data, validate_collection


class TestLoadManifest:
    def test_loads_valid_manifest(self, collected_dir):
        manifest = load_manifest(collected_dir)
        assert manifest["org_name"] == "Acme Corp"
        assert manifest["org_id"] == "org-abc-123"

    def test_missing_manifest_raises(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        with pytest.raises(FileNotFoundError):
            load_manifest(d)


class TestValidateCollection:
    def test_valid_collection_passes(self, collected_dir):
        errors = validate_collection(collected_dir)
        assert errors == []

    def test_missing_required_file(self, collected_dir):
        (collected_dir / "devices.json").unlink()
        errors = validate_collection(collected_dir)
        assert len(errors) == 1
        assert "devices.json" in errors[0]

    def test_missing_multiple_files(self, collected_dir):
        (collected_dir / "devices.json").unlink()
        (collected_dir / "trunks.json").unlink()
        errors = validate_collection(collected_dir)
        assert len(errors) == 2


class TestLoadCollectedData:
    def test_loads_all_files(self, collected_dir):
        data = load_collected_data(collected_dir)
        assert "manifest" in data
        assert "auto_attendants" in data
        assert "devices" in data
        assert isinstance(data["call_queue_details"], dict)
        assert isinstance(data["outgoing_permissions"], dict)

    def test_loads_detail_subdirectories(self, collected_dir):
        detail = {"id": "cq-1", "name": "Sales Queue", "callRecording": {"enabled": False}}
        (collected_dir / "call_queue_details" / "cq-1.json").write_text(json.dumps(detail))
        data = load_collected_data(collected_dir)
        assert "cq-1" in data["call_queue_details"]
        assert data["call_queue_details"]["cq-1"]["name"] == "Sales Queue"

    def test_loads_permissions_subdirectory(self, collected_dir):
        perm = {"id": "u-1", "callingPermissions": []}
        (collected_dir / "outgoing_permissions" / "u-1.json").write_text(json.dumps(perm))
        data = load_collected_data(collected_dir)
        assert "u-1" in data["outgoing_permissions"]
