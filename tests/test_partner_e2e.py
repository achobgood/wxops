"""End-to-end test: partner multi-org flow with mocked API responses.

Simulates a partner admin token that can see 3 orgs, selects one,
confirms via whoami, then validates that orgId is injected into
commands that accept it and NOT injected into commands that don't.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from wxcli.main import app
from wxcli.config import load_config, save_config, get_org_id, get_org_name

runner = CliRunner()

# --- Mock data ---

PARTNER_ORGS = {
    "items": [
        {"id": "ORG_PARTNER_001", "displayName": "Partner HQ"},
        {"id": "ORG_CUSTOMER_ACME", "displayName": "Acme Corp"},
        {"id": "ORG_CUSTOMER_GLOBEX", "displayName": "Globex Industries"},
    ]
}

SINGLE_ORG = {
    "items": [
        {"id": "ORG_SINGLE_001", "displayName": "My Company"},
    ]
}

MOCK_ME = MagicMock()
MOCK_ME.display_name = "Jane Partner"
MOCK_ME.emails = ["jane@partner.example.com"]
MOCK_ME.org_id = "ORG_PARTNER_001"
MOCK_ME.roles = None

MOCK_QUEUES = {"items": [{"id": "Q1", "name": "Sales Queue"}]}
MOCK_WEBHOOKS = {"items": [{"id": "W1", "targetUrl": "https://example.com"}]}


@pytest.fixture
def tmp_config(tmp_path):
    """Create a temp config with a mock token."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "profiles": {
            "default": {
                "token": "MOCK_PARTNER_TOKEN",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        }
    }))
    return config_path


@pytest.fixture
def config_with_org(tmp_path):
    """Config with org already selected (Acme Corp)."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "profiles": {
            "default": {
                "token": "MOCK_PARTNER_TOKEN",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "org_id": "ORG_CUSTOMER_ACME",
                "org_name": "Acme Corp",
            }
        }
    }))
    return config_path


# ===========================
# Phase 1: Configure + Detect
# ===========================

class TestConfigureMultiOrg:
    """Test the configure flow detects multiple orgs and prompts for selection."""

    def _make_config_patches(self, config_path):
        """Create patches that redirect config I/O to a temp path."""
        from wxcli.config import load_config as _lc, save_config as _sc, save_org as _so
        return {
            "wxcli.commands.configure.load_config": lambda path=None: _lc(config_path),
            "wxcli.commands.configure.save_config": lambda data, path=None: _sc(data, config_path),
            "wxcli.commands.configure.save_org": lambda oid, oname, path=None: _so(oid, oname, config_path),
        }

    def test_configure_detects_multi_org_and_selects(self, tmp_path):
        """Partner token → 3 orgs shown → user picks #2 (Acme Corp)."""
        config_path = tmp_path / "config.json"

        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME
        mock_api.session.rest_get.return_value = PARTNER_ORGS

        patches = self._make_config_patches(config_path)
        with patch("wxcli.commands.configure.WebexSimpleApi", return_value=mock_api), \
             patch("wxcli.commands.configure.load_config", side_effect=patches["wxcli.commands.configure.load_config"]), \
             patch("wxcli.commands.configure.save_config", side_effect=patches["wxcli.commands.configure.save_config"]), \
             patch("wxcli.commands.configure.save_org", side_effect=patches["wxcli.commands.configure.save_org"]):
            result = runner.invoke(app, ["configure"], input="MOCK_TOKEN\n2\n")

        assert result.exit_code == 0, result.output
        assert "Multiple organizations detected" in result.output
        assert "Acme Corp" in result.output
        assert "Globex Industries" in result.output
        assert "Target org set: Acme Corp" in result.output

        # Verify config was saved with org selection
        config = json.loads(config_path.read_text())
        assert config["profiles"]["default"]["org_id"] == "ORG_CUSTOMER_ACME"
        assert config["profiles"]["default"]["org_name"] == "Acme Corp"
        assert config["profiles"]["default"]["token"] == "MOCK_TOKEN"

    def test_configure_single_org_skips_prompt(self, tmp_path):
        """Single-org token → no org prompt shown."""
        config_path = tmp_path / "config.json"

        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME
        mock_api.session.rest_get.return_value = SINGLE_ORG

        patches = self._make_config_patches(config_path)
        with patch("wxcli.commands.configure.WebexSimpleApi", return_value=mock_api), \
             patch("wxcli.commands.configure.load_config", side_effect=patches["wxcli.commands.configure.load_config"]), \
             patch("wxcli.commands.configure.save_config", side_effect=patches["wxcli.commands.configure.save_config"]), \
             patch("wxcli.commands.configure.save_org", side_effect=patches["wxcli.commands.configure.save_org"]):
            result = runner.invoke(app, ["configure"], input="MOCK_TOKEN\n")

        assert result.exit_code == 0, result.output
        assert "Multiple organizations" not in result.output
        assert "Authenticated: Jane Partner" in result.output

        # No org_id in config
        config = json.loads(config_path.read_text())
        assert "org_id" not in config["profiles"]["default"]

    def test_configure_preserves_existing_org_on_reconfig(self, tmp_path):
        """Reconfiguring with a new token preserves existing org_id."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({
            "profiles": {"default": {
                "token": "OLD_TOKEN",
                "org_id": "ORG_CUSTOMER_ACME",
                "org_name": "Acme Corp",
            }}
        }))

        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME
        mock_api.session.rest_get.return_value = SINGLE_ORG

        patches = self._make_config_patches(config_path)
        with patch("wxcli.commands.configure.WebexSimpleApi", return_value=mock_api), \
             patch("wxcli.commands.configure.load_config", side_effect=patches["wxcli.commands.configure.load_config"]), \
             patch("wxcli.commands.configure.save_config", side_effect=patches["wxcli.commands.configure.save_config"]), \
             patch("wxcli.commands.configure.save_org", side_effect=patches["wxcli.commands.configure.save_org"]):
            result = runner.invoke(app, ["configure"], input="NEW_TOKEN\n")

        assert result.exit_code == 0, result.output
        config = json.loads(config_path.read_text())
        assert config["profiles"]["default"]["token"] == "NEW_TOKEN"
        assert config["profiles"]["default"]["org_id"] == "ORG_CUSTOMER_ACME"
        assert config["profiles"]["default"]["org_name"] == "Acme Corp"


# ===========================
# Phase 2: Whoami + Switch/Clear
# ===========================

class TestWhoamiAndOrgCommands:
    """Test whoami shows target org, switch-org switches, clear-org clears."""

    def test_whoami_shows_target_org(self, config_with_org):
        """whoami displays Target: line when org_id is set."""
        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME

        with patch("wxcli.main.get_api", return_value=mock_api), \
             patch("wxcli.main.get_expires_at", return_value="2099-01-01T00:00:00+00:00"), \
             patch("wxcli.main.get_org_id", return_value="ORG_CUSTOMER_ACME"), \
             patch("wxcli.main.get_org_name", return_value="Acme Corp"):
            result = runner.invoke(app, ["whoami"])

        assert result.exit_code == 0
        assert "User:  Jane Partner" in result.output
        assert "Org:   ORG_PARTNER_001" in result.output
        assert "Target: ORG_CUSTOMER_ACME  (Acme Corp)" in result.output

    def test_whoami_no_target_when_not_set(self, tmp_config):
        """whoami does NOT show Target: when no org_id is set."""
        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME

        with patch("wxcli.main.get_api", return_value=mock_api), \
             patch("wxcli.main.get_expires_at", return_value="2099-01-01T00:00:00+00:00"), \
             patch("wxcli.main.get_org_id", return_value=None), \
             patch("wxcli.main.get_org_name", return_value=None):
            result = runner.invoke(app, ["whoami"])

        assert result.exit_code == 0
        assert "Target:" not in result.output

    def test_clear_org_removes_config(self, config_with_org):
        """clear-org removes org_id and org_name from config."""
        with patch("wxcli.main.save_org") as mock_save:
            result = runner.invoke(app, ["clear-org"])

        assert result.exit_code == 0
        assert "Cleared target org" in result.output
        mock_save.assert_called_once_with(None, None)

    def test_switch_org_direct_id(self, config_with_org):
        """switch-org with direct orgId argument skips interactive prompt."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = {"displayName": "Globex Industries"}

        with patch("wxcli.main.resolve_token", return_value="MOCK_TOKEN"), \
             patch("wxcli.main.save_org") as mock_save, \
             patch("wxc_sdk.WebexSimpleApi", return_value=mock_api):
            result = runner.invoke(app, ["switch-org", "ORG_CUSTOMER_GLOBEX"])

        assert result.exit_code == 0
        assert "Target org set: Globex Industries" in result.output
        mock_save.assert_called_once_with("ORG_CUSTOMER_GLOBEX", "Globex Industries")


# ===========================
# Phase 3: orgId Injection
# ===========================

class TestOrgIdInjection:
    """Validate orgId appears in params for endpoints that accept it,
    and does NOT appear for endpoints that don't."""

    def test_call_queue_list_injects_orgid(self, config_with_org):
        """call-queue list should include orgId in request params."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = MOCK_QUEUES

        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["call-queue", "list", "-o", "json"])

        assert result.exit_code == 0
        # Verify the API was called with orgId in params
        call_args = mock_api.session.rest_get.call_args
        assert call_args is not None
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"

    def test_call_queue_show_injects_orgid(self, config_with_org):
        """call-queue show should include orgId in request params."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = {"id": "Q1", "name": "Sales"}

        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["call-queue", "show", "LOC1", "Q1", "-o", "json"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"

    def test_call_queue_delete_injects_orgid(self, config_with_org):
        """call-queue delete should include orgId in request params."""
        mock_api = MagicMock()

        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["call-queue", "delete", "LOC1", "Q1", "--force"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_delete.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"

    def test_webhooks_list_does_NOT_inject_orgid(self, config_with_org):
        """webhooks list should NOT include orgId — not in the spec for this endpoint."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = MOCK_WEBHOOKS

        with patch("wxcli.commands.webhooks.get_api", return_value=mock_api):
            result = runner.invoke(app, ["webhooks", "list", "-o", "json"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert "orgId" not in params

    def test_no_org_configured_skips_injection(self, tmp_config):
        """When no org_id is in config, orgId should NOT be in params."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = MOCK_QUEUES

        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value=None):
            result = runner.invoke(app, ["call-queue", "list", "-o", "json"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert "orgId" not in params


# ===========================
# Phase 4: Hand-coded commands
# ===========================

class TestHandCodedOrgIdInjection:
    """Validate hand-coded commands also inject orgId correctly."""

    def test_users_list_injects_orgid_via_sdk(self):
        """users list passes org_id to api.people.list()."""
        mock_api = MagicMock()
        mock_api.people.list.return_value = []

        with patch("wxcli.commands.users.get_api", return_value=mock_api), \
             patch("wxcli.commands.users.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["users", "list", "-o", "json"])

        assert result.exit_code == 0
        call_kwargs = mock_api.people.list.call_args.kwargs
        assert call_kwargs.get("org_id") == "ORG_CUSTOMER_ACME"

    def test_users_list_no_org_skips_sdk_param(self):
        """users list does NOT pass org_id when not configured."""
        mock_api = MagicMock()
        mock_api.people.list.return_value = []

        with patch("wxcli.commands.users.get_api", return_value=mock_api), \
             patch("wxcli.commands.users.get_org_id", return_value=None):
            result = runner.invoke(app, ["users", "list", "-o", "json"])

        assert result.exit_code == 0
        call_kwargs = mock_api.people.list.call_args.kwargs
        assert "org_id" not in call_kwargs

    def test_licenses_list_injects_orgid_via_sdk(self):
        """licenses list passes org_id to api.licenses.list()."""
        mock_api = MagicMock()
        mock_api.licenses.list.return_value = []

        with patch("wxcli.commands.licenses.get_api", return_value=mock_api), \
             patch("wxcli.commands.licenses.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["licenses", "list", "-o", "json"])

        assert result.exit_code == 0
        call_kwargs = mock_api.licenses.list.call_args.kwargs
        assert call_kwargs.get("org_id") == "ORG_CUSTOMER_ACME"

    def test_locations_list_injects_orgid_raw_http(self):
        """locations list includes orgId in raw HTTP params."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = {"items": []}

        with patch("wxcli.commands.locations.get_api", return_value=mock_api), \
             patch("wxcli.commands.locations.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["locations", "list", "-o", "json"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"

    def test_numbers_list_injects_orgid_raw_http(self):
        """numbers list includes orgId in raw HTTP params."""
        mock_api = MagicMock()
        mock_api.session.rest_get.return_value = {"phoneNumbers": []}

        with patch("wxcli.commands.numbers.get_api", return_value=mock_api), \
             patch("wxcli.commands.numbers.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["numbers", "list", "-o", "json"])

        assert result.exit_code == 0
        call_args = mock_api.session.rest_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"


# ===========================
# Phase 5: Full flow simulation
# ===========================

class TestFullPartnerFlow:
    """Simulate the complete partner experience: configure → confirm → operate."""

    def test_full_partner_journey(self, tmp_path):
        """
        1. Partner runs configure with multi-org token → selects Acme Corp
        2. whoami shows Target: Acme Corp
        3. call-queue list sends orgId=ORG_CUSTOMER_ACME
        4. webhooks list does NOT send orgId
        5. switch-org to Globex
        6. call-queue list now sends orgId=ORG_CUSTOMER_GLOBEX
        7. clear-org removes targeting
        8. call-queue list no longer sends orgId
        """
        config_path = tmp_path / "config.json"

        # Step 1: Configure
        from wxcli.config import load_config as _lc, save_config as _sc, save_org as _so
        mock_api = MagicMock()
        mock_api.people.me.return_value = MOCK_ME
        mock_api.session.rest_get.return_value = PARTNER_ORGS

        with patch("wxcli.commands.configure.WebexSimpleApi", return_value=mock_api), \
             patch("wxcli.commands.configure.load_config", side_effect=lambda path=None: _lc(config_path)), \
             patch("wxcli.commands.configure.save_config", side_effect=lambda data, path=None: _sc(data, config_path)), \
             patch("wxcli.commands.configure.save_org", side_effect=lambda oid, oname, path=None: _so(oid, oname, config_path)):
            result = runner.invoke(app, ["configure"], input="MOCK_TOKEN\n2\n")
        assert result.exit_code == 0, result.output
        assert "Target org set: Acme Corp" in result.output

        # Verify config state after configure
        config = json.loads(config_path.read_text())
        assert config["profiles"]["default"]["org_id"] == "ORG_CUSTOMER_ACME"

        # Step 2: whoami shows target
        with patch("wxcli.main.get_api", return_value=mock_api), \
             patch("wxcli.main.get_expires_at", return_value="2099-01-01T00:00:00+00:00"), \
             patch("wxcli.main.get_org_id", return_value="ORG_CUSTOMER_ACME"), \
             patch("wxcli.main.get_org_name", return_value="Acme Corp"):
            result = runner.invoke(app, ["whoami"])
        assert "Target: ORG_CUSTOMER_ACME  (Acme Corp)" in result.output

        # Step 3: call-queue list sends orgId
        mock_api.session.rest_get.return_value = MOCK_QUEUES
        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value="ORG_CUSTOMER_ACME"):
            result = runner.invoke(app, ["call-queue", "list", "-o", "json"])
        params = mock_api.session.rest_get.call_args.kwargs.get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_ACME"

        # Step 4: webhooks list does NOT send orgId
        mock_api.session.rest_get.return_value = MOCK_WEBHOOKS
        with patch("wxcli.commands.webhooks.get_api", return_value=mock_api):
            result = runner.invoke(app, ["webhooks", "list", "-o", "json"])
        params = mock_api.session.rest_get.call_args.kwargs.get("params", {})
        assert "orgId" not in params

        # Step 5: switch-org to Globex
        mock_api.session.rest_get.return_value = {"displayName": "Globex Industries"}
        with patch("wxcli.main.resolve_token", return_value="MOCK_TOKEN"), \
             patch("wxcli.main.save_org") as mock_save, \
             patch("wxc_sdk.WebexSimpleApi", return_value=mock_api):
            result = runner.invoke(app, ["switch-org", "ORG_CUSTOMER_GLOBEX"])
        assert "Target org set: Globex Industries" in result.output
        mock_save.assert_called_with("ORG_CUSTOMER_GLOBEX", "Globex Industries")

        # Step 6: call-queue list now sends new orgId
        mock_api.session.rest_get.return_value = MOCK_QUEUES
        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value="ORG_CUSTOMER_GLOBEX"):
            result = runner.invoke(app, ["call-queue", "list", "-o", "json"])
        params = mock_api.session.rest_get.call_args.kwargs.get("params", {})
        assert params.get("orgId") == "ORG_CUSTOMER_GLOBEX"

        # Step 7: clear-org
        with patch("wxcli.main.save_org") as mock_save:
            result = runner.invoke(app, ["clear-org"])
        assert "Cleared target org" in result.output

        # Step 8: call-queue list no longer sends orgId
        mock_api.session.rest_get.return_value = MOCK_QUEUES
        with patch("wxcli.commands.call_queue.get_api", return_value=mock_api), \
             patch("wxcli.commands.call_queue.get_org_id", return_value=None):
            result = runner.invoke(app, ["call-queue", "list", "-o", "json"])
        params = mock_api.session.rest_get.call_args.kwargs.get("params", {})
        assert "orgId" not in params
