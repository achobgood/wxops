import json
import pytest
from pathlib import Path

from wxcli.config import get_org_id, get_org_name, save_org, load_config


@pytest.fixture
def tmp_config(tmp_path):
    return tmp_path / "config.json"


def test_get_org_id_missing(tmp_config):
    """get_org_id returns None when no org_id in config."""
    tmp_config.write_text(json.dumps({"profiles": {"default": {"token": "t"}}}))
    assert get_org_id(tmp_config) is None


def test_get_org_id_present(tmp_config):
    """get_org_id returns the stored org_id."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "abc123", "org_name": "Acme"}}
    }))
    assert get_org_id(tmp_config) == "abc123"


def test_get_org_name_present(tmp_config):
    """get_org_name returns the stored org_name."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "abc123", "org_name": "Acme"}}
    }))
    assert get_org_name(tmp_config) == "Acme"


def test_save_org_sets_fields(tmp_config):
    """save_org writes org_id and org_name to config."""
    tmp_config.write_text(json.dumps({"profiles": {"default": {"token": "t"}}}))
    save_org("org1", "Org One", tmp_config)
    config = load_config(tmp_config)
    assert config["profiles"]["default"]["org_id"] == "org1"
    assert config["profiles"]["default"]["org_name"] == "Org One"
    assert config["profiles"]["default"]["token"] == "t"


def test_save_org_clears_fields(tmp_config):
    """save_org(None, None) removes org_id and org_name."""
    tmp_config.write_text(json.dumps({
        "profiles": {"default": {"token": "t", "org_id": "old", "org_name": "Old"}}
    }))
    save_org(None, None, tmp_config)
    config = load_config(tmp_config)
    assert "org_id" not in config["profiles"]["default"]
    assert "org_name" not in config["profiles"]["default"]
    assert config["profiles"]["default"]["token"] == "t"


def test_get_org_id_no_config_file(tmp_path):
    """get_org_id returns None when config file doesn't exist."""
    assert get_org_id(tmp_path / "nonexistent.json") is None
