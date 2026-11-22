import os
import stat
from pathlib import Path

import pytest

from wxcli.config import (
    load_config, save_config, get_token, save_cc_region, save_flow_store_url, save_org,
)

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


# ── The config holds the bearer token: readable by its owner only ──────────

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")


def _mode(path):
    return stat.S_IMODE(path.stat().st_mode)


@posix_only
def test_first_save_creates_the_file_0600(tmp_path):
    path = tmp_path / "config.json"
    save_config({"profiles": {"default": {"token": "t"}}}, path)
    assert _mode(path) == 0o600


@posix_only
def test_save_tightens_a_pre_existing_0644_file(tmp_path):
    """Older wxcli wrote the file with a plain open(): 0o644 under umask 022."""
    path = tmp_path / "config.json"
    path.write_text('{"profiles": {"default": {"token": "old"}}}')
    os.chmod(path, 0o644)
    save_config({"profiles": {"default": {"token": "new"}}}, path)
    assert _mode(path) == 0o600
    assert get_token(path) == "new"


@posix_only
def test_save_creates_a_missing_parent_dir_0700(tmp_path):
    path = tmp_path / "wxcli-home" / "config.json"
    save_config({"profiles": {}}, path)
    assert _mode(path.parent) == 0o700


@posix_only
def test_save_leaves_an_existing_parent_dir_alone(tmp_path):
    parent = tmp_path / "existing"
    parent.mkdir()
    os.chmod(parent, 0o755)
    save_config({"profiles": {}}, parent / "config.json")
    assert _mode(parent) == 0o755


@posix_only
@pytest.mark.parametrize("write", [
    lambda p: save_org("ORG", "Org", p),
    lambda p: save_cc_region("eu1", p),
    lambda p: save_flow_store_url("https://example.invalid/flow-store", p),
], ids=["save_org", "save_cc_region", "save_flow_store_url"])
def test_every_config_writer_leaves_the_file_0600(tmp_path, write):
    path = tmp_path / "config.json"
    path.write_text('{"profiles": {"default": {"token": "t"}}}')
    os.chmod(path, 0o644)
    write(path)
    assert _mode(path) == 0o600
    assert get_token(path) == "t"
