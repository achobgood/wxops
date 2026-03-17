import json
from pathlib import Path
from wxcli.config import load_config, save_config, get_token

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
