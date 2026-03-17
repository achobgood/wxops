import os
import json
from unittest.mock import patch
from wxcli.auth import resolve_token

def test_resolve_token_from_env():
    with patch.dict(os.environ, {"WEBEX_ACCESS_TOKEN": "env-token"}, clear=False):
        assert resolve_token(config_path=None) == "env-token"

def test_resolve_token_fallback_env():
    env = os.environ.copy()
    env.pop("WEBEX_ACCESS_TOKEN", None)
    env["WEBEX_TOKEN"] = "fallback-token"
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        assert resolve_token(config_path=None) == "fallback-token"

def test_resolve_token_from_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "profiles": {"default": {"token": "config-token"}}
    }))
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        os.environ.pop("WEBEX_TOKEN", None)
        assert resolve_token(config_path=config_path) == "config-token"

def test_resolve_token_none_when_missing(tmp_path):
    config_path = tmp_path / "nonexistent.json"
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEBEX_ACCESS_TOKEN", None)
        os.environ.pop("WEBEX_TOKEN", None)
        assert resolve_token(config_path=config_path) is None
