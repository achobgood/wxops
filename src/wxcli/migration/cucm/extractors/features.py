"""Feature extractors for CUCM AXL.

Pulls Hunt Pilots, Hunt Lists, Line Groups, CTI Route Points, Call Park,
Pickup Groups, Time Schedules, and Time Periods.

Sources:
- 02b-cucm-extraction.md §2.5 (feature extraction)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)

# AXL Gotchas (discovered test bed expansion 2026-03-24):
# - addCallPickupGroup with <members>/<directoryNumber> fails on CUCM 15.0
#   (null priority FK constraint). Use empty create + updateLine workaround.
# - No listPagingGroup/getPagingGroup AXL methods exist. Paging requires
#   InformaCast/Cisco Paging Server. CanonicalPagingGroup is manual-only.
# - CTI Route Points may require SCCP instead of SIP on some device pools.
# - TimePeriod monthOfYear: 3-letter abbreviations only (Dec, Jan, etc.)

# ------------------------------------------------------------------
# ReturnedTags constants
# ------------------------------------------------------------------

# Verified: listHuntPilot accepts these fields per WSDL LHuntPilot schema.
# Fields like mohSourceId, maxCallersInQueue, huntTimerCallPick, overflowDestination,
# enabled are only on getHuntPilot.
HUNT_PILOT_LIST_RETURNED_TAGS = {
    "pattern": "", "description": "", "routePartitionName": "",
    "huntListName": "",
}

# Verified: list operations do NOT accept nested fields (members, lines).
# Use list tags for discovery, get operations for full detail.
HUNT_LIST_LIST_RETURNED_TAGS = {
    "name": "", "description": "",
}

LINE_GROUP_LIST_RETURNED_TAGS = {
    "name": "", "distributionAlgorithm": "",
}

CTI_RP_LIST_RETURNED_TAGS = {
    "name": "", "description": "", "devicePoolName": "", "callingSearchSpaceName": "",
}

CALL_PARK_RETURNED_TAGS = {
    "pattern": "", "description": "", "routePartitionName": "",
}

PICKUP_GROUP_LIST_RETURNED_TAGS = {
    "name": "",
}

TIME_SCHEDULE_LIST_RETURNED_TAGS = {
    "name": "",
}

TIME_PERIOD_LIST_RETURNED_TAGS = {
    "name": "",
}


class FeatureExtractor(BaseExtractor):
    """Extract calling features from CUCM AXL.

    Covers Hunt Pilots, Hunt Lists, Line Groups, CTI Route Points,
    Call Park, Pickup Groups, Time Schedules, and Time Periods.

    (from 02b §2.5)
    """

    name = "features"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run all feature extractions.

        Returns an ExtractionResult summarizing total objects and errors.
        """
        result = ExtractionResult(extractor=self.name)

        self.results["hunt_pilots"] = self._extract_hunt_pilots(result)
        self.results["hunt_lists"] = self._extract_hunt_lists(result)
        self.results["line_groups"] = self._extract_line_groups(result)
        self.results["cti_route_points"] = self._extract_cti_route_points(result)
        self.results["call_parks"] = self._extract_call_parks(result)
        self.results["pickup_groups"] = self._extract_pickup_groups(result)
        self.results["time_schedules"] = self._extract_time_schedules(result)
        self.results["time_periods"] = self._extract_time_periods(result)
        self.results["executive_assistant_pairs"] = self._extract_executive_assistant_pairs(result)
        self.results["executive_settings"] = self._extract_executive_settings(result)

        return result

    # ------------------------------------------------------------------
    # Common list+get pattern
    # ------------------------------------------------------------------

    def _list_and_get(
        self,
        result: ExtractionResult,
        list_method: str,
        get_method: str,
        search_criteria: dict[str, str],
        returned_tags: dict[str, str],
        name_field: str = "name",
    ) -> list[dict[str, Any]]:
        """Common pattern: paginated list then per-object get.

        On get failure (exception or None), the object is skipped and counted
        as failed — consistent with DeviceExtractor and RoutingExtractor.
        """
        items: list[dict[str, Any]] = []
        try:
            summaries = self.paginated_list(list_method, search_criteria, returned_tags)
        except Exception as exc:
            msg = f"{list_method} failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return items

        for summary in summaries:
            result.total += 1
            obj_name = ref_value(summary.get(name_field)) or summary.get(name_field, "")
            if not obj_name:
                result.failed += 1
                result.errors.append(f"{list_method} returned object with no {name_field}")
                continue

            try:
                kwargs = {name_field: obj_name}
                # Hunt pilots are looked up by pattern + partition, not name
                if name_field == "pattern":
                    partition = ref_value(summary.get("routePartitionName"))
                    kwargs["routePartitionName"] = partition or ""
                detail = self.get_detail(get_method, **kwargs)
            except Exception as exc:
                result.failed += 1
                msg = f"{get_method}({obj_name}): {exc}"
                logger.warning("[%s] %s", self.name, msg)
                result.errors.append(msg)
                continue

            if detail is None:
                result.failed += 1
                result.errors.append(f"{get_method} returned None for {obj_name}")
                continue

            items.append(detail)

        return items

    # ------------------------------------------------------------------
    # Hunt Pilots
    # ------------------------------------------------------------------

    def _extract_hunt_pilots(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract hunt pilots. Verified against live CUCM 15.0 2026-03-23."""
        return self._list_and_get(
            result, "listHuntPilot", "getHuntPilot",
            {"pattern": "%"}, HUNT_PILOT_LIST_RETURNED_TAGS, name_field="pattern",
        )

    # ------------------------------------------------------------------
    # Hunt Lists
    # ------------------------------------------------------------------

    def _extract_hunt_lists(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract hunt lists. Verified via pipeline execution against CUCM 15.0 testbed."""
        return self._list_and_get(
            result, "listHuntList", "getHuntList",
            {"name": "%"}, HUNT_LIST_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # Line Groups
    # ------------------------------------------------------------------

    def _extract_line_groups(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract line groups. Verified via pipeline execution against CUCM 15.0 testbed."""
        return self._list_and_get(
            result, "listLineGroup", "getLineGroup",
            {"name": "%"}, LINE_GROUP_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # CTI Route Points
    # ------------------------------------------------------------------

    def _extract_cti_route_points(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract CTI route points. Verified via pipeline execution against CUCM 15.0 testbed."""
        return self._list_and_get(
            result, "listCtiRoutePoint", "getCtiRoutePoint",
            {"name": "%"}, CTI_RP_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # Call Parks — list only, no get needed
    # ------------------------------------------------------------------

    def _extract_call_parks(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract call parks (list only, no get needed). Verified via pipeline execution."""
        try:
            parks = self.paginated_list(
                "listCallPark", {"pattern": "%"}, CALL_PARK_RETURNED_TAGS,
            )
            result.total += len(parks)
            return parks
        except Exception as exc:
            msg = f"listCallPark failed: {exc}"
            logger.error("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return []

    # ------------------------------------------------------------------
    # Pickup Groups
    # ------------------------------------------------------------------

    def _extract_pickup_groups(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract pickup groups. Verified against live CUCM 15.0 2026-03-24."""
        return self._list_and_get(
            result, "listCallPickupGroup", "getCallPickupGroup",
            {"pattern": "%"}, PICKUP_GROUP_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # Time Schedules
    # ------------------------------------------------------------------

    def _extract_time_schedules(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract time schedules. Verified via pipeline execution against CUCM 15.0 testbed."""
        return self._list_and_get(
            result, "listTimeSchedule", "getTimeSchedule",
            {"name": "%"}, TIME_SCHEDULE_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # Time Periods
    # ------------------------------------------------------------------

    def _extract_time_periods(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract time periods. Verified via pipeline execution against CUCM 15.0 testbed."""
        return self._list_and_get(
            result, "listTimePeriod", "getTimePeriod",
            {"name": "%"}, TIME_PERIOD_LIST_RETURNED_TAGS,
        )

    # ------------------------------------------------------------------
    # Executive/Assistant Pairs (SQL query)
    # ------------------------------------------------------------------

    def _extract_executive_assistant_pairs(
        self, result: ExtractionResult,
    ) -> list[dict[str, Any]]:
        """Extract executive/assistant pairings via SQL query."""
        try:
            rows = self.conn.execute_sql(
                "SELECT "
                "exec_user.userid AS executive_userid, "
                "asst_user.userid AS assistant_userid, "
                "ea.fkexecutive AS executive_pkid, "
                "ea.fkassistant AS assistant_pkid "
                "FROM executiveassistant ea "
                "JOIN enduser exec_user ON exec_user.pkid = ea.fkexecutive "
                "JOIN enduser asst_user ON asst_user.pkid = ea.fkassistant"
            )
        except Exception as exc:
            msg = f"executiveassistant SQL query failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return []
        result.total += len(rows)
        return rows

    # ------------------------------------------------------------------
    # Executive/Assistant Settings (SQL query)
    # ------------------------------------------------------------------

    def _extract_executive_settings(
        self, result: ExtractionResult,
    ) -> list[dict[str, Any]]:
        """Extract executive/assistant service subscriptions via SQL query."""
        try:
            rows = self.conn.execute_sql(
                "SELECT eu.userid, s.name AS service_name, s.servicetype "
                "FROM enduser eu "
                "JOIN endusersubscribedservice euss ON euss.fkenduser = eu.pkid "
                "JOIN subscribedservice s ON s.pkid = euss.fksubscribedservice "
                "WHERE s.name IN ('Executive', 'Executive-Assistant')"
            )
        except Exception as exc:
            msg = f"executive settings SQL query failed: {exc}"
            logger.warning("[%s] %s", self.name, msg)
            result.errors.append(msg)
            return []
        result.total += len(rows)
        return rows
