"""Transform mappers — CUCM canonical objects to Webex canonical objects.

Each mapper reads resolved canonical objects (post-normalization, post-cross-reference)
from the MigrationStore and produces Webex-ready canonical objects plus decisions for
anything that can't be cleanly mapped.

(from 03b-transform-mappers.md, mapper contract and execution order)
"""

from wxcli.migration.transform.mappers.base import (
    Mapper,
    accept_option,
    decision_to_store_dict,
    manual_option,
    skip_option,
)
from wxcli.migration.transform.mappers.button_template_mapper import ButtonTemplateMapper
from wxcli.migration.transform.mappers.call_forwarding_mapper import CallForwardingMapper
from wxcli.migration.transform.mappers.css_mapper import CSSMapper
from wxcli.migration.transform.mappers.monitoring_mapper import MonitoringMapper
from wxcli.migration.transform.mappers.device_mapper import DeviceMapper
from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper
from wxcli.migration.transform.mappers.line_mapper import LineMapper
from wxcli.migration.transform.mappers.location_mapper import LocationMapper
from wxcli.migration.transform.mappers.routing_mapper import RoutingMapper
from wxcli.migration.transform.mappers.user_mapper import UserMapper
from wxcli.migration.transform.mappers.voicemail_mapper import VoicemailMapper
from wxcli.migration.transform.mappers.voicemail_group_mapper import VoicemailGroupMapper
from wxcli.migration.transform.mappers.device_layout_mapper import DeviceLayoutMapper
from wxcli.migration.transform.mappers.softkey_mapper import SoftkeyMapper
from wxcli.migration.transform.mappers.device_profile_mapper import DeviceProfileMapper
from wxcli.migration.transform.mappers.e911_mapper import E911Mapper
from wxcli.migration.transform.mappers.moh_mapper import MOHMapper
from wxcli.migration.transform.mappers.snr_mapper import SNRMapper
from wxcli.migration.transform.mappers.announcement_mapper import AnnouncementMapper
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper
from wxcli.migration.transform.mappers.executive_assistant_mapper import ExecutiveAssistantMapper
from wxcli.migration.transform.mappers.receptionist_mapper import ReceptionistMapper
from wxcli.migration.transform.mappers.device_settings_mapper import DeviceSettingsMapper
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper
from wxcli.migration.transform.mappers.ecbn_mapper import EcbnMapper

__all__ = [
    "Mapper",
    "LocationMapper",
    "UserMapper",
    "LineMapper",
    "DeviceMapper",
    "WorkspaceMapper",
    "RoutingMapper",
    "FeatureMapper",
    "CSSMapper",
    "VoicemailMapper",
    "VoicemailGroupMapper",
    "CallForwardingMapper",
    "MonitoringMapper",
    "ButtonTemplateMapper",
    "DeviceLayoutMapper",
    "SoftkeyMapper",
    "SNRMapper",
    "E911Mapper",
    "MOHMapper",
    "AnnouncementMapper",
    "DeviceProfileMapper",
    "ExecutiveAssistantMapper",
    "ReceptionistMapper",
    "DeviceSettingsMapper",
    "CallSettingsMapper",
    "EcbnMapper",
    "skip_option",
    "manual_option",
    "accept_option",
    "decision_to_store_dict",
]
