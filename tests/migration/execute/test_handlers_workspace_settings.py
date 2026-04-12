"""Regression tests for handle_workspace_configure_settings."""
from wxcli.migration.execute.handlers import handle_workspace_configure_settings


def _ctx() -> dict:
    return {"orgId": "test-org", "base_url": "https://webexapis.com/v1"}


class TestWorkspaceConfigureSettingsHandler:
    def test_dnd_uses_telephony_config_url(self):
        """PUTs must target /telephony/config/workspaces/{id}/doNotDisturb.

        Regression guard: do NOT let this handler revert to the old
        /workspaces/{id}/features/{name} path — that path returns 404
        for doNotDisturb and voicemail, breaking the migration silently.
        """
        data = {"call_settings": {"doNotDisturb": {"enabled": True}}}
        deps = {"workspace:conf-3a": "WS_WEBEX_ID_12345"}
        calls = handle_workspace_configure_settings(data, deps, _ctx())

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "PUT"
        assert "/telephony/config/workspaces/WS_WEBEX_ID_12345/doNotDisturb" in url
        assert "/workspaces/WS_WEBEX_ID_12345/features/" not in url
        assert body == {"enabled": True}

    def test_multiple_settings_produce_multiple_puts(self):
        """Each key in call_settings becomes one PUT call."""
        data = {
            "call_settings": {
                "doNotDisturb": {"enabled": False, "ringSplashEnabled": False},
                "voicemail": {"enabled": False},
            }
        }
        deps = {"workspace:lobby-1": "WS_ABC"}
        calls = handle_workspace_configure_settings(data, deps, _ctx())

        assert len(calls) == 2
        urls = {c[1] for c in calls}
        assert any("doNotDisturb" in u for u in urls)
        assert any("voicemail" in u for u in urls)
        assert all("telephony/config/workspaces/WS_ABC" in u for u in urls)

    def test_empty_settings_returns_empty_list(self):
        """No call_settings → no API calls (engine marks op completed as a no-op)."""
        data = {"call_settings": {}}
        deps = {"workspace:conf-x": "WS_X"}
        assert handle_workspace_configure_settings(data, deps, _ctx()) == []

    def test_missing_workspace_dep_returns_empty(self):
        """If deps don't contain a workspace:* entry, handler is a no-op."""
        data = {"call_settings": {"doNotDisturb": {"enabled": True}}}
        deps = {"user:jsmith": "PERSON_ID"}
        assert handle_workspace_configure_settings(data, deps, _ctx()) == []
