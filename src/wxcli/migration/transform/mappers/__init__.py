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
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper

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
    "CallForwardingMapper",
    "MonitoringMapper",
    "skip_option",
    "manual_option",
    "accept_option",
    "decision_to_store_dict",
]
