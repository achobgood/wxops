import typer
from datetime import datetime, timezone

from wxcli import __version__
from wxcli.auth import get_api, resolve_token, WebexApi, WebexSession
from wxcli.config import get_expires_at, get_org_id, get_org_name, save_org

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
    me = api.session.rest_get("https://webexapis.com/v1/people/me")

    display_name = me.get("displayName", "")
    email = (me.get("emails") or ["unknown"])[0]
    org_id = me.get("orgId", "")
    typer.echo(f"User:  {display_name} ({email})")
    typer.echo(f"Org:   {org_id}")

    target_org_id = get_org_id()
    target_org_name = get_org_name()
    if target_org_id:
        typer.echo(f"Target: {target_org_id}  ({target_org_name})")

    roles = me.get("roles")
    if roles:
        typer.echo(f"Roles: {', '.join(roles)}")

    expires = get_expires_at()
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            remaining = exp_dt - now
            if remaining.total_seconds() > 0:
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                if hours < 2:
                    typer.echo(f"Token: expires in {hours}h {minutes}m — consider refreshing soon")
                else:
                    typer.echo(f"Token: expires in {hours}h {minutes}m")
        except ValueError:
            pass


@app.command("switch-org")
def switch_org(
    org_id: str = typer.Argument(None, help="orgId to switch to (skip interactive prompt)"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Switch target organization for partner multi-org tokens."""
    token = resolve_token()
    if not token:
        typer.echo("Error: No token found. Run 'wxcli configure' first.", err=True)
        raise typer.Exit(1)

    api = WebexApi(WebexSession(token))

    if org_id:
        # Direct switch — resolve org name
        try:
            org = api.session.rest_get(f"https://webexapis.com/v1/organizations/{org_id}")
            org_name = org.get("displayName", "Unknown")
        except Exception:
            org_name = "Unknown"
        save_org(org_id, org_name)
        typer.echo(f"Target org set: {org_name} ({org_id})")
        return

    # Interactive — list orgs
    try:
        result = api.session.rest_get("https://webexapis.com/v1/organizations")
        items = result.get("items", []) if isinstance(result, dict) else []
    except Exception as e:
        typer.echo(f"Error listing organizations: {e}", err=True)
        raise typer.Exit(1)

    if len(items) <= 1:
        typer.echo("Single-org token — no org switching needed.")
        return

    typer.echo(f"\nAvailable organizations:\n")
    for i, org in enumerate(items, 1):
        name = org.get("displayName", "Unknown")
        oid = org.get("id", "")
        typer.echo(f"  {i}. {name:<30s} ({oid})")

    typer.echo()
    choice = typer.prompt(f"Select target org [1-{len(items)}]", type=int)
    if choice < 1 or choice > len(items):
        typer.echo("Invalid selection.", err=True)
        raise typer.Exit(1)

    selected = items[choice - 1]
    save_org(selected.get("id"), selected.get("displayName"))
    typer.echo(f"\nTarget org set: {selected.get('displayName')} ({selected.get('id')})")


@app.command("clear-org")
def clear_org():
    """Clear target organization — commands will target your own org."""
    save_org(None, None)
    typer.echo("Cleared target org. Commands will now target your own organization.")


@app.command("set-cc-region")
def set_cc_region(
    region: str = typer.Argument(
        help="Contact Center region: us1, eu1, eu2, anz1, ca1, jp1, sg1"
    ),
):
    """Set the Contact Center API region for cc-* commands."""
    from wxcli.config import CC_REGIONS, save_cc_region
    if region not in CC_REGIONS:
        typer.echo(f"Error: Unknown region '{region}'. Valid: {', '.join(sorted(CC_REGIONS))}", err=True)
        raise typer.Exit(1)
    save_cc_region(region)
    typer.echo(f"CC region set: {region} ({CC_REGIONS[region]})")


# Hand-coded modules
from wxcli.commands.configure import app as configure_app
from wxcli.commands.locations import app as locations_app
from wxcli.commands.numbers import app as numbers_app
from wxcli.commands.licenses import app as licenses_app
from wxcli.commands.cucm import app as cucm_app

app.add_typer(configure_app, name="configure")
app.add_typer(locations_app, name="locations")
app.add_typer(numbers_app, name="numbers")
app.add_typer(licenses_app, name="licenses")
app.add_typer(cucm_app, name="cucm")

from wxcli.commands.cleanup import app as cleanup_app
app.add_typer(cleanup_app, name="cleanup")

# Auto-generated converged recordings CRUD + hand-written download/export
from wxcli.commands.converged_recordings import app as converged_recordings_app
app.add_typer(converged_recordings_app, name="converged-recordings")
from wxcli.commands import converged_recordings_export
converged_recordings_export.register(converged_recordings_app)

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
from wxcli.commands.admin_recordings import app as admin_recordings_app
app.add_typer(admin_recordings_app, name="admin-recordings")
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
from wxcli.commands.text_to_speech import app as text_to_speech_app
app.add_typer(text_to_speech_app, name="text-to-speech")
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
from wxcli.commands.mode_management import app as mode_management_app
app.add_typer(mode_management_app, name="mode-management")
from wxcli.commands.pstn import app as pstn_app
app.add_typer(pstn_app, name="pstn")
from wxcli.commands.partner_reports import app as partner_reports_app
app.add_typer(partner_reports_app, name="partner-reports")
from wxcli.commands.people import app as people_app
app.add_typer(people_app, name="people")
app.add_typer(people_app, name="users")  # alias: users → people (replaced hand-coded users.py)
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
from wxcli.commands.my_call_settings import app as my_call_settings_app
app.add_typer(my_call_settings_app, name="my-call-settings")
from wxcli.commands.workspaces import app as workspaces_app
app.add_typer(workspaces_app, name="workspaces")

# Auto-generated from admin spec (specs/webex-admin.json)
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

# Auto-generated from device spec (specs/webex-device.json)
from wxcli.commands.device_configurations import app as device_configurations_app
app.add_typer(device_configurations_app, name="device-configurations")
from wxcli.commands.workspace_personalization import app as workspace_personalization_app
app.add_typer(workspace_personalization_app, name="workspace-personalization")
from wxcli.commands.xapi import app as xapi_app
app.add_typer(xapi_app, name="xapi")

# Auto-generated from messaging spec (specs/webex-messaging.json)
from wxcli.commands.attachment_actions import app as attachment_actions_app
app.add_typer(attachment_actions_app, name="attachment-actions")
from wxcli.commands.ecm import app as ecm_app
app.add_typer(ecm_app, name="ecm")
from wxcli.commands.hds import app as hds_app
app.add_typer(hds_app, name="hds")
from wxcli.commands.memberships import app as memberships_app
app.add_typer(memberships_app, name="memberships")
from wxcli.commands.messages import app as messages_app
app.add_typer(messages_app, name="messages")
from wxcli.commands.room_tabs import app as room_tabs_app
app.add_typer(room_tabs_app, name="room-tabs")
from wxcli.commands.rooms import app as rooms_app
app.add_typer(rooms_app, name="rooms")
from wxcli.commands.team_memberships import app as team_memberships_app
app.add_typer(team_memberships_app, name="team-memberships")
from wxcli.commands.teams import app as teams_app
app.add_typer(teams_app, name="teams")
from wxcli.commands.webhooks import app as webhooks_app
app.add_typer(webhooks_app, name="webhooks")

# Auto-generated from meetings spec (specs/webex-meetings.json)
from wxcli.commands.meeting_chats import app as meeting_chats_app
app.add_typer(meeting_chats_app, name="meeting-chats")
from wxcli.commands.meeting_captions import app as meeting_captions_app
app.add_typer(meeting_captions_app, name="meeting-captions")
from wxcli.commands.meeting_invitees import app as meeting_invitees_app
app.add_typer(meeting_invitees_app, name="meeting-invitees")
from wxcli.commands.meeting_messages import app as meeting_messages_app
app.add_typer(meeting_messages_app, name="meeting-messages")
from wxcli.commands.meeting_polls import app as meeting_polls_app
app.add_typer(meeting_polls_app, name="meeting-polls")
from wxcli.commands.meeting_qa import app as meeting_qa_app
app.add_typer(meeting_qa_app, name="meeting-qa")
from wxcli.commands.meetings import app as meetings_app
app.add_typer(meetings_app, name="meetings")
from wxcli.commands.meeting_reports import app as meeting_reports_app
app.add_typer(meeting_reports_app, name="meeting-reports")
from wxcli.commands.meeting_participants import app as meeting_participants_app
app.add_typer(meeting_participants_app, name="meeting-participants")
from wxcli.commands.meeting_preferences import app as meeting_preferences_app
app.add_typer(meeting_preferences_app, name="meeting-preferences")
from wxcli.commands.meeting_session_types import app as meeting_session_types_app
app.add_typer(meeting_session_types_app, name="meeting-session-types")
from wxcli.commands.meeting_site import app as meeting_site_app
app.add_typer(meeting_site_app, name="meeting-site")
from wxcli.commands.meeting_slido import app as meeting_slido_app
app.add_typer(meeting_slido_app, name="meeting-slido")
from wxcli.commands.meeting_summaries import app as meeting_summaries_app
app.add_typer(meeting_summaries_app, name="meeting-summaries")
from wxcli.commands.meeting_tracking_codes import app as meeting_tracking_codes_app
app.add_typer(meeting_tracking_codes_app, name="meeting-tracking-codes")
from wxcli.commands.meeting_transcripts import app as meeting_transcripts_app
app.add_typer(meeting_transcripts_app, name="meeting-transcripts")
from wxcli.commands.video_mesh import app as video_mesh_app
app.add_typer(video_mesh_app, name="video-mesh")

# Auto-generated from contact center spec (specs/webex-contact-center.json)
from wxcli.commands.cc_ai_assistant import app as cc_ai_assistant_app
app.add_typer(cc_ai_assistant_app, name="cc-ai-assistant")
from wxcli.commands.cc_ai_feature import app as cc_ai_feature_app
app.add_typer(cc_ai_feature_app, name="cc-ai-feature")
from wxcli.commands.cc_address_book import app as cc_address_book_app
app.add_typer(cc_address_book_app, name="cc-address-book")
from wxcli.commands.cc_agent_greetings import app as cc_agent_greetings_app
app.add_typer(cc_agent_greetings_app, name="cc-agent-greetings")
from wxcli.commands.cc_agent_summaries import app as cc_agent_summaries_app
app.add_typer(cc_agent_summaries_app, name="cc-agent-summaries")
from wxcli.commands.cc_agent_wellbeing import app as cc_agent_wellbeing_app
app.add_typer(cc_agent_wellbeing_app, name="cc-agent-wellbeing")
from wxcli.commands.cc_agents import app as cc_agents_app
app.add_typer(cc_agents_app, name="cc-agents")
from wxcli.commands.cc_audio_files import app as cc_audio_files_app
app.add_typer(cc_audio_files_app, name="cc-audio-files")
from wxcli.commands.cc_auto_csat import app as cc_auto_csat_app
app.add_typer(cc_auto_csat_app, name="cc-auto-csat")
from wxcli.commands.cc_aux_code import app as cc_aux_code_app
app.add_typer(cc_aux_code_app, name="cc-aux-code")
from wxcli.commands.cc_business_hour import app as cc_business_hour_app
app.add_typer(cc_business_hour_app, name="cc-business-hour")
from wxcli.commands.cc_call_monitoring import app as cc_call_monitoring_app
app.add_typer(cc_call_monitoring_app, name="cc-call-monitoring")
from wxcli.commands.cc_callbacks import app as cc_callbacks_app
app.add_typer(cc_callbacks_app, name="cc-callbacks")
from wxcli.commands.cc_campaign import app as cc_campaign_app
app.add_typer(cc_campaign_app, name="cc-campaign")
from wxcli.commands.cc_captures import app as cc_captures_app
app.add_typer(cc_captures_app, name="cc-captures")
from wxcli.commands.cc_contact_list import app as cc_contact_list_app
app.add_typer(cc_contact_list_app, name="cc-contact-list")
from wxcli.commands.cc_contact_number import app as cc_contact_number_app
app.add_typer(cc_contact_number_app, name="cc-contact-number")
from wxcli.commands.cc_data_sources import app as cc_data_sources_app
app.add_typer(cc_data_sources_app, name="cc-data-sources")
from wxcli.commands.cc_desktop_layout import app as cc_desktop_layout_app
app.add_typer(cc_desktop_layout_app, name="cc-desktop-layout")
from wxcli.commands.cc_desktop_profile import app as cc_desktop_profile_app
app.add_typer(cc_desktop_profile_app, name="cc-desktop-profile")
from wxcli.commands.cc_dial_number import app as cc_dial_number_app
app.add_typer(cc_dial_number_app, name="cc-dial-number")
from wxcli.commands.cc_dial_plan import app as cc_dial_plan_app
app.add_typer(cc_dial_plan_app, name="cc-dial-plan")
from wxcli.commands.cc_dnc import app as cc_dnc_app
app.add_typer(cc_dnc_app, name="cc-dnc")
from wxcli.commands.cc_entry_point import app as cc_entry_point_app
app.add_typer(cc_entry_point_app, name="cc-entry-point")
from wxcli.commands.cc_ewt import app as cc_ewt_app
app.add_typer(cc_ewt_app, name="cc-ewt")
from wxcli.commands.cc_flow import app as cc_flow_app
app.add_typer(cc_flow_app, name="cc-flow")
from wxcli.commands.cc_global_vars import app as cc_global_vars_app
app.add_typer(cc_global_vars_app, name="cc-global-vars")
from wxcli.commands.cc_holiday_list import app as cc_holiday_list_app
app.add_typer(cc_holiday_list_app, name="cc-holiday-list")
from wxcli.commands.cc_journey import app as cc_journey_app
app.add_typer(cc_journey_app, name="cc-journey")
from wxcli.commands.cc_multimedia_profile import app as cc_multimedia_profile_app
app.add_typer(cc_multimedia_profile_app, name="cc-multimedia-profile")
from wxcli.commands.cc_notification import app as cc_notification_app
app.add_typer(cc_notification_app, name="cc-notification")
from wxcli.commands.cc_outdial_ani import app as cc_outdial_ani_app
app.add_typer(cc_outdial_ani_app, name="cc-outdial-ani")
from wxcli.commands.cc_overrides import app as cc_overrides_app
app.add_typer(cc_overrides_app, name="cc-overrides")
from wxcli.commands.cc_queue import app as cc_queue_app
app.add_typer(cc_queue_app, name="cc-queue")
from wxcli.commands.cc_queue_stats import app as cc_queue_stats_app
app.add_typer(cc_queue_stats_app, name="cc-queue-stats")
from wxcli.commands.cc_realtime import app as cc_realtime_app
app.add_typer(cc_realtime_app, name="cc-realtime")
from wxcli.commands.cc_resource_collection import app as cc_resource_collection_app
app.add_typer(cc_resource_collection_app, name="cc-resource-collection")
from wxcli.commands.cc_search import app as cc_search_app
app.add_typer(cc_search_app, name="cc-search")
from wxcli.commands.cc_site import app as cc_site_app
app.add_typer(cc_site_app, name="cc-site")
from wxcli.commands.cc_skill import app as cc_skill_app
app.add_typer(cc_skill_app, name="cc-skill")
from wxcli.commands.cc_skill_profile import app as cc_skill_profile_app
app.add_typer(cc_skill_profile_app, name="cc-skill-profile")
from wxcli.commands.cc_subscriptions import app as cc_subscriptions_app
app.add_typer(cc_subscriptions_app, name="cc-subscriptions")
from wxcli.commands.cc_summaries import app as cc_summaries_app
app.add_typer(cc_summaries_app, name="cc-summaries")
from wxcli.commands.cc_tasks import app as cc_tasks_app
app.add_typer(cc_tasks_app, name="cc-tasks")
from wxcli.commands.cc_team import app as cc_team_app
app.add_typer(cc_team_app, name="cc-team")
from wxcli.commands.cc_user_profiles import app as cc_user_profiles_app
app.add_typer(cc_user_profiles_app, name="cc-user-profiles")
from wxcli.commands.cc_users import app as cc_users_app
app.add_typer(cc_users_app, name="cc-users")
from wxcli.commands.cc_work_types import app as cc_work_types_app
app.add_typer(cc_work_types_app, name="cc-work-types")
