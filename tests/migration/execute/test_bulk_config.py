"""Verify bulk_device_threshold is seeded into config.json defaults."""

from __future__ import annotations

import json

from wxcli.commands.cucm_config import DEFAULT_CONFIG, load_config


def test_default_config_has_bulk_threshold():
    assert "bulk_device_threshold" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["bulk_device_threshold"] == 100


def test_load_config_returns_default_when_missing(tmp_path):
    config = load_config(tmp_path)
    assert config["bulk_device_threshold"] == 100


def test_load_config_honors_user_override(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"bulk_device_threshold": 500}))
    config = load_config(tmp_path)
    assert config["bulk_device_threshold"] == 500


def test_load_config_bulk_disabled_with_large_value(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"bulk_device_threshold": 999999}))
    config = load_config(tmp_path)
    assert config["bulk_device_threshold"] == 999999
