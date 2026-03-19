import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api
from wxcli.config import get_expires_at

app = typer.Typer(
    name="wxcli",
    help="Webex Calling CLI — provision and manage Webex Calling from the terminal.",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"wxcli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
):
    pass


@app.command()
def whoami(
    debug: bool = typer.Option(False, "--debug", help="Show debug output"),
):
    """Show current authenticated user and org."""
    api = get_api(debug=debug)
    me = api.people.me()

    typer.echo(f"User:  {me.display_name} ({me.emails[0]})")
    typer.echo(f"Org:   {me.org_id}")

    roles = getattr(me, "roles", None)
    if roles:
        typer.echo(f"Roles: {', '.join(roles)}")

    expires = get_expires_at()
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            remaining = exp_dt - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            if remaining.total_seconds() <= 0:
                typer.echo("Token: EXPIRED — run 'wxcli configure'", err=True)
            elif hours < 2:
                typer.echo(f"Token: expires in {hours}h {minutes}m — consider refreshing soon")
            else:
                typer.echo(f"Token: expires in {hours}h {minutes}m")
        except ValueError:
            pass


# Hand-coded modules
from wxcli.commands.configure import app as configure_app
from wxcli.commands.locations import app as locations_app
from wxcli.commands.users import app as users_app
from wxcli.commands.numbers import app as numbers_app
from wxcli.commands.licenses import app as licenses_app

app.add_typer(configure_app, name="configure")
app.add_typer(locations_app, name="locations")
app.add_typer(users_app, name="users")
app.add_typer(numbers_app, name="numbers")
app.add_typer(licenses_app, name="licenses")

# Auto-generated from OpenAPI spec
from wxcli.commands.call_controls import app as call_controls_app
app.add_typer(call_controls_app, name="call-controls")
from wxcli.commands.cq_playlists import app as cq_playlists_app
app.add_typer(cq_playlists_app, name="cq-playlists")
from wxcli.commands.call_routing import app as call_routing_app
app.add_typer(call_routing_app, name="call-routing")
from wxcli.commands.caller_reputation import app as caller_reputation_app
app.add_typer(caller_reputation_app, name="caller-reputation")
from wxcli.commands.calling_service import app as calling_service_app
app.add_typer(calling_service_app, name="calling-service")
from wxcli.commands.client_settings import app as client_settings_app
app.add_typer(client_settings_app, name="client-settings")
from wxcli.commands.conference import app as conference_app
app.add_typer(conference_app, name="conference")
from wxcli.commands.recordings import app as recordings_app
app.add_typer(recordings_app, name="recordings")
from wxcli.commands.dect_devices import app as dect_devices_app
app.add_typer(dect_devices_app, name="dect-devices")
from wxcli.commands.device_settings import app as device_settings_app
app.add_typer(device_settings_app, name="device-settings")
from wxcli.commands.device_dynamic_settings import app as device_dynamic_settings_app
app.add_typer(device_dynamic_settings_app, name="device-dynamic-settings")
from wxcli.commands.devices import app as devices_app
app.add_typer(devices_app, name="devices")
from wxcli.commands.emergency_services import app as emergency_services_app
app.add_typer(emergency_services_app, name="emergency-services")
from wxcli.commands.external_voicemail import app as external_voicemail_app
app.add_typer(external_voicemail_app, name="external-voicemail")
from wxcli.commands.auto_attendant import app as auto_attendant_app
app.add_typer(auto_attendant_app, name="auto-attendant")
from wxcli.commands.call_park import app as call_park_app
app.add_typer(call_park_app, name="call-park")
from wxcli.commands.call_pickup import app as call_pickup_app
app.add_typer(call_pickup_app, name="call-pickup")
from wxcli.commands.call_queue import app as call_queue_app
app.add_typer(call_queue_app, name="call-queue")
from wxcli.commands.hunt_group import app as hunt_group_app
app.add_typer(hunt_group_app, name="hunt-group")
from wxcli.commands.paging_group import app as paging_group_app
app.add_typer(paging_group_app, name="paging-group")
from wxcli.commands.announcement_playlists import app as announcement_playlists_app
app.add_typer(announcement_playlists_app, name="announcement-playlists")
from wxcli.commands.announcements import app as announcements_app
app.add_typer(announcements_app, name="announcements")
from wxcli.commands.call_recording import app as call_recording_app
app.add_typer(call_recording_app, name="call-recording")
from wxcli.commands.cx_essentials import app as cx_essentials_app
app.add_typer(cx_essentials_app, name="cx-essentials")
from wxcli.commands.hot_desking_portal import app as hot_desking_portal_app
app.add_typer(hot_desking_portal_app, name="hot-desking-portal")
from wxcli.commands.operating_modes import app as operating_modes_app
app.add_typer(operating_modes_app, name="operating-modes")
from wxcli.commands.single_number_reach import app as single_number_reach_app
app.add_typer(single_number_reach_app, name="single-number-reach")
from wxcli.commands.virtual_extensions import app as virtual_extensions_app
app.add_typer(virtual_extensions_app, name="virtual-extensions")
from wxcli.commands.hot_desk import app as hot_desk_app
app.add_typer(hot_desk_app, name="hot-desk")
from wxcli.commands.location_settings import app as location_settings_app
app.add_typer(location_settings_app, name="location-settings")
from wxcli.commands.location_schedules import app as location_schedules_app
app.add_typer(location_schedules_app, name="location-schedules")
from wxcli.commands.location_voicemail import app as location_voicemail_app
app.add_typer(location_voicemail_app, name="location-voicemail")
from wxcli.commands.location_call_handling import app as location_call_handling_app
app.add_typer(location_call_handling_app, name="location-call-handling")
from wxcli.commands.locations_api import app as locations_api_app
app.add_typer(locations_api_app, name="locations-api")
from wxcli.commands.mode_management import app as mode_management_app
app.add_typer(mode_management_app, name="mode-management")
from wxcli.commands.numbers_api import app as numbers_api_app
app.add_typer(numbers_api_app, name="numbers-api")
from wxcli.commands.pstn import app as pstn_app
app.add_typer(pstn_app, name="pstn")
from wxcli.commands.partner_reports import app as partner_reports_app
app.add_typer(partner_reports_app, name="partner-reports")
from wxcli.commands.people import app as people_app
app.add_typer(people_app, name="people")
from wxcli.commands.recording_report import app as recording_report_app
app.add_typer(recording_report_app, name="recording-report")
from wxcli.commands.reports import app as reports_app
app.add_typer(reports_app, name="reports")
from wxcli.commands.cdr import app as cdr_app
app.add_typer(cdr_app, name="cdr")
from wxcli.commands.user_settings import app as user_settings_app
app.add_typer(user_settings_app, name="user-settings")
from wxcli.commands.virtual_line_settings import app as virtual_line_settings_app
app.add_typer(virtual_line_settings_app, name="virtual-line-settings")
from wxcli.commands.workspace_settings import app as workspace_settings_app
app.add_typer(workspace_settings_app, name="workspace-settings")
from wxcli.commands.workspaces import app as workspaces_app
app.add_typer(workspaces_app, name="workspaces")

# Auto-generated from admin spec (webex-admin.json)
from wxcli.commands.domains import app as domains_app
app.add_typer(domains_app, name="domains")
from wxcli.commands.audit_events import app as audit_events_app
app.add_typer(audit_events_app, name="audit-events")
from wxcli.commands.archive_users import app as archive_users_app
app.add_typer(archive_users_app, name="archive-users")
from wxcli.commands.authorizations import app as authorizations_app
app.add_typer(authorizations_app, name="authorizations")
from wxcli.commands.scim_bulk import app as scim_bulk_app
app.add_typer(scim_bulk_app, name="scim-bulk")
from wxcli.commands.classifications import app as classifications_app
app.add_typer(classifications_app, name="classifications")
from wxcli.commands.data_sources import app as data_sources_app
app.add_typer(data_sources_app, name="data-sources")
from wxcli.commands.events import app as events_app
app.add_typer(events_app, name="events")
from wxcli.commands.groups import app as groups_app
app.add_typer(groups_app, name="groups")
from wxcli.commands.guest_management import app as guest_management_app
app.add_typer(guest_management_app, name="guest-management")
from wxcli.commands.analytics import app as analytics_app
app.add_typer(analytics_app, name="analytics")
from wxcli.commands.hybrid_clusters import app as hybrid_clusters_app
app.add_typer(hybrid_clusters_app, name="hybrid-clusters")
from wxcli.commands.hybrid_connectors import app as hybrid_connectors_app
app.add_typer(hybrid_connectors_app, name="hybrid-connectors")
from wxcli.commands.identity_org import app as identity_org_app
app.add_typer(identity_org_app, name="identity-org")
from wxcli.commands.licenses_api import app as licenses_api_app
app.add_typer(licenses_api_app, name="licenses-api")
from wxcli.commands.live_monitoring import app as live_monitoring_app
app.add_typer(live_monitoring_app, name="live-monitoring")
from wxcli.commands.meeting_qualities import app as meeting_qualities_app
app.add_typer(meeting_qualities_app, name="meeting-qualities")
from wxcli.commands.org_contacts import app as org_contacts_app
app.add_typer(org_contacts_app, name="org-contacts")
from wxcli.commands.organizations import app as organizations_app
app.add_typer(organizations_app, name="organizations")
from wxcli.commands.partner_admins import app as partner_admins_app
app.add_typer(partner_admins_app, name="partner-admins")
from wxcli.commands.partner_tags import app as partner_tags_app
app.add_typer(partner_tags_app, name="partner-tags")
from wxcli.commands.admin_recordings import app as admin_recordings_app
app.add_typer(admin_recordings_app, name="admin-recordings")
from wxcli.commands.report_templates import app as report_templates_app
app.add_typer(report_templates_app, name="report-templates")
from wxcli.commands.resource_group_memberships import app as resource_group_memberships_app
app.add_typer(resource_group_memberships_app, name="resource-group-memberships")
from wxcli.commands.resource_groups import app as resource_groups_app
app.add_typer(resource_groups_app, name="resource-groups")
from wxcli.commands.roles import app as roles_app
app.add_typer(roles_app, name="roles")
from wxcli.commands.scim_groups import app as scim_groups_app
app.add_typer(scim_groups_app, name="scim-groups")
from wxcli.commands.scim_schemas import app as scim_schemas_app
app.add_typer(scim_schemas_app, name="scim-schemas")
from wxcli.commands.scim_users import app as scim_users_app
app.add_typer(scim_users_app, name="scim-users")
from wxcli.commands.security_audit import app as security_audit_app
app.add_typer(security_audit_app, name="security-audit")
from wxcli.commands.activation_email import app as activation_email_app
app.add_typer(activation_email_app, name="activation-email")
from wxcli.commands.service_apps import app as service_apps_app
app.add_typer(service_apps_app, name="service-apps")
from wxcli.commands.org_settings import app as org_settings_app
app.add_typer(org_settings_app, name="org-settings")
from wxcli.commands.workspace_locations import app as workspace_locations_app
app.add_typer(workspace_locations_app, name="workspace-locations")
from wxcli.commands.workspace_metrics import app as workspace_metrics_app
app.add_typer(workspace_metrics_app, name="workspace-metrics")
