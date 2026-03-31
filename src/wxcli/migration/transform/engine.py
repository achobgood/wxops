"""TransformEngine — orchestrates all 14 mappers in dependency order.

Runs each mapper sequentially in MAPPER_ORDER (tier-sorted), aggregates
decisions and errors into a single TransformResult. If a mapper raises
an exception, the engine logs the error, records a MapperError, and
continues to the next mapper. Downstream mappers that depend on the
failed mapper's output will find no objects and produce MISSING_DATA
decisions naturally.

(from 03b-transform-mappers.md section 13, TransformEngine)
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from wxcli.migration.models import (
    MapperError,
    TransformResult,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.base import (
    Mapper,
    decision_to_store_dict,
)
from wxcli.migration.transform.mappers.css_mapper import CSSMapper
from wxcli.migration.transform.mappers.device_mapper import DeviceMapper
from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper
from wxcli.migration.transform.mappers.line_mapper import LineMapper
from wxcli.migration.transform.mappers.location_mapper import LocationMapper
from wxcli.migration.transform.mappers.routing_mapper import RoutingMapper
from wxcli.migration.transform.mappers.user_mapper import UserMapper
from wxcli.migration.transform.mappers.call_forwarding_mapper import CallForwardingMapper
from wxcli.migration.transform.mappers.monitoring_mapper import MonitoringMapper
from wxcli.migration.transform.mappers.voicemail_mapper import VoicemailMapper
from wxcli.migration.transform.mappers.button_template_mapper import ButtonTemplateMapper
from wxcli.migration.transform.mappers.device_layout_mapper import DeviceLayoutMapper
from wxcli.migration.transform.mappers.device_profile_mapper import DeviceProfileMapper
from wxcli.migration.transform.mappers.e911_mapper import E911Mapper
from wxcli.migration.transform.mappers.announcement_mapper import AnnouncementMapper
from wxcli.migration.transform.mappers.moh_mapper import MOHMapper
from wxcli.migration.transform.mappers.snr_mapper import SNRMapper
from wxcli.migration.transform.mappers.softkey_mapper import SoftkeyMapper
from wxcli.migration.transform.mappers.workspace_mapper import WorkspaceMapper
from wxcli.migration.transform.mappers.call_settings_mapper import CallSettingsMapper

logger = logging.getLogger(__name__)

# Dependency-sorted execution order.
# (from 03b-transform-mappers.md section 13: MAPPER_ORDER)
#
# Tier 0: LocationMapper, RoutingMapper (no upstream dependencies)
# Tier 2: UserMapper, LineMapper, WorkspaceMapper (depend on locations)
# Tier 3: DeviceMapper (depends on users, lines)
# Tier 4: FeatureMapper (depends on users, lines, locations)
# Tier 5: CSSMapper (depends on routing_mapper output), VoicemailMapper (depends on users)
MAPPER_ORDER: list[type[Mapper]] = [
    LocationMapper,       # Tier 0 — produces locations
    RoutingMapper,        # Tier 0-2 (trunks, route groups, dial plans)
    UserMapper,           # Tier 2 (depends on locations)
    LineMapper,           # Tier 2 (depends on locations for country code)
    WorkspaceMapper,      # Tier 2 (depends on locations)
    DeviceMapper,         # Tier 3 (depends on users, lines)
    FeatureMapper,        # Tier 4 (depends on users, lines, locations)
    CSSMapper,            # Tier 5 (depends on routing_mapper output)
    VoicemailMapper,      # Tier 5 (depends on users)
    CallForwardingMapper, # Tier 6 (depends on users, phones/device cross-refs)
    MonitoringMapper,     # Tier 6 (depends on users, phones, lines)
    SNRMapper,            # Tier 6 (depends on users — remote destinations)
    DeviceProfileMapper,  # Tier 6 (depends on users, workspaces — EM/hot desking)
    E911Mapper,           # Tier 6 (depends on locations — E911 advisory)
    MOHMapper,            # Tier 6 (depends on locations — MOH audio sources)
    AnnouncementMapper,   # Tier 6 (depends on locations, features — announcements)
    SoftkeyMapper,        # Tier 6 (depends on devices for phone model info)
    ButtonTemplateMapper, # Tier 6 (depends on devices for phone→template cross-refs)
    CallSettingsMapper,   # Tier 6 (depends on users — call settings enrichment)
    DeviceLayoutMapper,   # Tier 7 (depends on button_template, monitoring, line, device mappers)
]


class TransformEngine:
    """Orchestrates all 14 transform mappers in dependency order.

    (from 03b-transform-mappers.md section 13)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """
        Args:
            config: Optional configuration dict passed to mappers that need it.
                Keys used:
                    default_language        -> LocationMapper
                    default_country         -> LocationMapper, LineMapper
                    outside_dial_digit      -> LocationMapper, RoutingMapper, CSSMapper
                    site_prefix_rules       -> LocationMapper, LineMapper
                    create_method           -> UserMapper
                    include_phoneless_users -> UserMapper
                    country_code            -> RoutingMapper, CSSMapper
                    category_rules          -> CSSMapper
        """
        self.config = config or {}

    def run(self, store: MigrationStore) -> TransformResult:
        """Run all 14 mappers in dependency order.

        Failure handling: if a mapper raises an exception, log the error,
        record a MapperError, and continue to the next mapper. Downstream
        mappers that depend on the failed mapper's output will find no objects
        and produce MISSING_DATA decisions naturally.

        Returns TransformResult with aggregated decisions and any mapper errors.
        """
        result = TransformResult()

        for mapper_cls in MAPPER_ORDER:
            mapper = self._instantiate_mapper(mapper_cls)
            mapper_name = mapper.name or mapper_cls.__name__

            logger.info("Running mapper: %s", mapper_name)
            try:
                mapper_result = mapper.map(store)

                # Save decisions to store and aggregate into result
                for decision in mapper_result.decisions:
                    store.save_decision(decision_to_store_dict(decision))
                    result.decisions.append(decision)

                logger.info(
                    "Mapper %s complete: %d created, %d updated, %d decisions",
                    mapper_name,
                    mapper_result.objects_created,
                    mapper_result.objects_updated,
                    len(mapper_result.decisions),
                )

            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    "Mapper %s failed with %s: %s",
                    mapper_name,
                    type(exc).__name__,
                    exc,
                )
                result.errors.append(
                    MapperError(
                        mapper_name=mapper_name,
                        error_message=str(exc),
                        traceback=tb,
                    )
                )
                # Continue to next mapper — do NOT abort

        return result

    def _instantiate_mapper(self, mapper_cls: type[Mapper]) -> Mapper:
        """Create a mapper instance with the appropriate config subset.

        Each mapper's __init__ takes different keyword arguments.  We inspect
        the mapper class and pass the relevant keys from self.config.
        """
        cfg = self.config

        if mapper_cls is LocationMapper:
            return LocationMapper(
                default_language=cfg.get("default_language", "en_us"),
                default_country=cfg.get("default_country", "US"),
                outside_dial_digit=str(cfg.get("outside_dial_digit", "9")),
                site_prefix_rules=cfg.get("site_prefix_rules"),
            )

        if mapper_cls is RoutingMapper:
            return RoutingMapper(
                country_code=cfg.get("country_code", "+1"),
                outside_dial_digit=str(cfg.get("outside_dial_digit", "9")),
            )

        if mapper_cls is UserMapper:
            return UserMapper(
                create_method=cfg.get("create_method", "people_api"),
                include_phoneless_users=cfg.get("include_phoneless_users", False),
            )

        if mapper_cls is LineMapper:
            return LineMapper(
                default_country_code=cfg.get("default_country", "US"),
                site_prefix_rules=cfg.get("site_prefix_rules"),
            )

        if mapper_cls is WorkspaceMapper:
            return WorkspaceMapper()

        if mapper_cls is DeviceMapper:
            return DeviceMapper()

        if mapper_cls is FeatureMapper:
            return FeatureMapper()

        if mapper_cls is CSSMapper:
            return CSSMapper(
                category_rules=cfg.get("category_rules"),
                country_code=cfg.get("country_code", "+1"),
                outside_dial_digit=str(cfg.get("outside_dial_digit", "9")),
            )

        if mapper_cls is VoicemailMapper:
            return VoicemailMapper()

        if mapper_cls is CallForwardingMapper:
            return CallForwardingMapper()

        if mapper_cls is MonitoringMapper:
            return MonitoringMapper()

        if mapper_cls is SoftkeyMapper:
            return SoftkeyMapper()

        if mapper_cls is ButtonTemplateMapper:
            return ButtonTemplateMapper()

        if mapper_cls is MOHMapper:
            return MOHMapper()

        if mapper_cls is AnnouncementMapper:
            return AnnouncementMapper()

        if mapper_cls is DeviceLayoutMapper:
            return DeviceLayoutMapper()

        if mapper_cls is CallSettingsMapper:
            return CallSettingsMapper()

        # Fallback: attempt no-arg construction
        return mapper_cls()  # type: ignore[call-arg]
