"""CLI smoke tests — verify command registration and --help without hitting live API."""

import pytest
from wxcli.main import app


# All command group names registered in main.py
COMMAND_GROUPS = [
    # Hand-coded
    "configure", "locations", "users", "numbers", "licenses",
    # Calling spec
    "call-controls", "cq-playlists", "call-routing", "caller-reputation",
    "calling-service", "client-settings", "conference", "recordings",
    "dect-devices", "device-settings", "device-dynamic-settings", "devices",
    "emergency-services", "external-voicemail", "auto-attendant", "call-park",
    "call-pickup", "call-queue", "hunt-group", "paging-group",
    "announcement-playlists", "announcements", "call-recording",
    "cx-essentials", "hot-desking-portal", "operating-modes",
    "single-number-reach", "virtual-extensions", "hot-desk",
    "location-settings", "location-schedules", "location-voicemail",
    "location-call-handling", "locations-api", "mode-management",
    "numbers-api", "pstn", "partner-reports", "people",
    "recording-report", "reports", "cdr", "user-settings",
    "virtual-line-settings", "workspace-settings", "workspaces",
    # Admin spec
    "domains", "audit-events", "archive-users", "authorizations",
    "scim-bulk", "classifications", "data-sources", "events", "groups",
    "guest-management", "analytics", "hybrid-clusters", "hybrid-connectors",
    "identity-org", "licenses-api", "live-monitoring", "meeting-qualities",
    "org-contacts", "organizations", "partner-admins", "partner-tags",
    "admin-recordings", "report-templates", "resource-group-memberships",
    "resource-groups", "roles", "scim-groups", "scim-schemas", "scim-users",
    "security-audit", "activation-email", "service-apps", "org-settings",
    "workspace-locations", "workspace-metrics",
    # Device spec
    "device-configurations", "workspace-personalization", "xapi",
    # Messaging spec
    "attachment-actions", "ecm", "hds", "memberships", "messages",
    "room-tabs", "rooms", "team-memberships", "teams", "webhooks",
]


class TestMainApp:
    """Test the top-level wxcli app."""

    def test_main_help(self, runner):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "wxcli" in result.output.lower()

    def test_version_flag(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "wxcli" in result.output

    def test_no_args_shows_help(self, runner):
        result = runner.invoke(app, [])
        # no_args_is_help=True causes exit code 0 on some typer versions, 2 on others
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "wxcli" in result.output.lower()


class TestCommandGroupRegistration:
    """Verify every command group is registered and responds to --help."""

    @pytest.mark.parametrize("group", COMMAND_GROUPS)
    def test_group_help(self, runner, group):
        result = runner.invoke(app, [group, "--help"])
        assert result.exit_code == 0, (
            f"{group} --help failed (exit {result.exit_code}): {result.output}"
        )
        assert "Usage" in result.output or "Options" in result.output, (
            f"{group} --help produced unexpected output: {result.output[:200]}"
        )


class TestCommandGroupCount:
    """Verify the expected number of command groups are registered."""

    def test_expected_group_count(self):
        # main.py registers command groups via add_typer + the 'whoami' command
        # Count the registered typer sub-apps
        registered = [
            g.name for g in getattr(app, "registered_groups", [])
            if g.name
        ]
        # Should have ~100 groups; fail if we drop below 90 (regression guard)
        assert len(registered) >= 90, (
            f"Only {len(registered)} command groups registered, expected 90+. "
            f"Check main.py imports."
        )
