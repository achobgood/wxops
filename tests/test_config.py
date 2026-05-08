import json
from pathlib import Path
import pytest
from wxcli.config import load_config, save_config, get_token, get_fs_base_url, get_fs_project_id, FS_DATACENTERS

def test_load_config_missing_file(tmp_path):
    config = load_config(tmp_path / "config.json")
    assert config == {"profiles": {}}

def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    data = {"profiles": {"default": {"token": "abc123", "expires_at": "2026-03-17T04:00:00Z"}}}
    save_config(data, path)
    loaded = load_config(path)
    assert loaded == data

def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "subdir" / "config.json"
    save_config({"profiles": {}}, path)
    assert path.exists()

def test_get_token(tmp_path):
    path = tmp_path / "config.json"
    save_config({"profiles": {"default": {"token": "mytoken"}}}, path)
    assert get_token(path) == "mytoken"

def test_get_token_missing(tmp_path):
    assert get_token(tmp_path / "nope.json") is None


class TestFlowStoreConfig:
    def test_fs_datacenters_has_intgus1(self):
        assert "intgus1" in FS_DATACENTERS

    def test_fs_datacenters_has_us1(self):
        assert "us1" in FS_DATACENTERS

    def test_get_fs_base_url_default(self, tmp_path):
        """Default datacenter returns intgus1 URL."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        url = get_fs_base_url(path=config_path)
        assert "intgus1" in url
        assert url.endswith("/flow-store")

    def test_get_fs_base_url_configured(self, tmp_path):
        """Configured datacenter returns correct URL."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"profiles": {"default": {"fs_datacenter": "us1"}}}))
        url = get_fs_base_url(path=config_path)
        assert "us1" in url
        assert "intgus1" not in url

    def test_get_fs_project_id_not_configured_exits(self, tmp_path):
        """Missing project ID raises SystemExit with helpful message."""
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        with pytest.raises(SystemExit, match="project ID not configured"):
            get_fs_project_id(path=config_path)

    def test_get_fs_project_id_configured(self, tmp_path):
        """Configured project ID is returned."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"profiles": {"default": {"fs_project_id": "61829605da1d142ee8104588"}}}))
        pid = get_fs_project_id(path=config_path)
        assert pid == "61829605da1d142ee8104588"
