"""Routing extractor — partitions, CSS, route patterns, gateways,
SIP trunks, route groups, route lists, and translation patterns.

Covers 8 object types that define CUCM call routing topology.

Sources:
- 02b-cucm-extraction.md §2.4 (routing extraction, all 8 types)
- 02b-cucm-extraction.md §3 (base extractor, pagination)
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.connection import AXLConnection
from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult
from wxcli.migration.cucm.extractors.helpers import ref_value, to_list

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# ReturnedTags constants — one per AXL object type (from 02b §2.4)
# ------------------------------------------------------------------

PARTITION_RETURNED_TAGS = {'name': '', 'description': ''}

# Verified: listCss does NOT accept 'members' — only getCss returns members.
# List with name+description only, then getCss for full member ordering.
CSS_LIST_RETURNED_TAGS = {'name': '', 'description': ''}

# Verified against live CUCM 15.0 (2026-03-23):
# - 'destination' is NOT a valid listRoutePattern returnedTag; route targets
#   require getRoutePattern for full resolution
# - 'networkLocation' and 'prefixDigitsOut' confirmed present in list response
ROUTE_PATTERN_RETURNED_TAGS = {
    'pattern': '', 'routePartitionName': '',
    'blockEnable': '', 'description': '', 'calledPartyTransformationMask': '',
    'callingPartyTransformationMask': '', 'prefixDigitsOut': '', 'networkLocation': '',
}

# Verified: listGateway does NOT return devicePoolName — only domainName,
# description, product, protocol. Use getGateway for devicePoolName.
GATEWAY_RETURNED_TAGS = {
    'domainName': '', 'description': '', 'product': '', 'protocol': '',
}

# Verified against live CUCM 15.0 (2026-03-23):
# - listSipTrunk does NOT accept 'destinations' — only getSipTrunk returns those
# - getSipTrunk returns destinations.destination[].addressIpv4, .port, .sortOrder
# - sipTrunkType returns values like 'None(Default)'
SIP_TRUNK_LIST_RETURNED_TAGS = {
    'name': '', 'description': '', 'devicePoolName': '',
    'sipProfileName': '', 'securityProfileName': '',
    'sipTrunkType': '',
}

# Verified: list schemas are restrictive. Use minimal tags for discovery, get for detail.
ROUTE_GROUP_LIST_RETURNED_TAGS = {'name': ''}
ROUTE_LIST_LIST_RETURNED_TAGS = {'name': ''}

TRANSLATION_PATTERN_RETURNED_TAGS = {
    'pattern': '', 'calledPartyTransformationMask': '', 'description': '',
    'routePartitionName': '',
}


class RoutingExtractor(BaseExtractor):
    """Extract CUCM routing configuration — 8 object types.

    (from 02b §2.4)
    """

    name = "routing"

    def __init__(self, connection: AXLConnection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Extract all 8 routing object types and aggregate results."""
        result = ExtractionResult(extractor=self.name)

        # Each sub-method populates self.results[key] and returns (count, errors)
        extractors = [
            ("partitions", self._extract_partitions),
            ("css_list", self._extract_css),
            ("route_patterns", self._extract_route_patterns),
            ("gateways", self._extract_gateways),
            ("sip_trunks", self._extract_sip_trunks),
            ("route_groups", self._extract_route_groups),
            ("route_lists", self._extract_route_lists),
            ("translation_patterns", self._extract_translation_patterns),
        ]

        for key, extract_fn in extractors:
            count, errors = extract_fn()
            result.total += count
            result.failed += len(errors)
            result.errors.extend(errors)

        logger.info(
            "[%s] Extracted %d total objects (%d failed)",
            self.name, result.success_count, result.failed,
        )
        return result

    # ------------------------------------------------------------------
    # Partitions — list only (simple objects)
    # ------------------------------------------------------------------

    def _extract_partitions(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing partitions...", self.name)
        partitions = self.paginated_list(
            method_name="listRoutePartition",
            search_criteria={"name": "%"},
            returned_tags=PARTITION_RETURNED_TAGS,
        )
        self.results["partitions"] = partitions
        logger.info("[%s] Found %d partitions", self.name, len(partitions))
        return len(partitions), []

    # ------------------------------------------------------------------
    # CSS — list + get for full ordered members (CRITICAL: preserve ordering)
    # ------------------------------------------------------------------

    def _extract_css(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing calling search spaces...", self.name)
        css_summaries = self.paginated_list(
            method_name="listCss",
            search_criteria={"name": "%"},
            returned_tags=CSS_LIST_RETURNED_TAGS,
        )
        logger.info("[%s] Found %d CSS", self.name, len(css_summaries))

        css_list: list[dict[str, Any]] = []
        errors: list[str] = []
        for summary in css_summaries:
            css_name = ref_value(summary.get("name")) or summary.get("name")
            if not css_name:
                errors.append("CSS with no name in listCss result")
                continue

            detail = self._get_css_detail(css_name)
            if detail is None:
                errors.append(f"getCss failed for {css_name}")
                continue

            css_list.append(detail)

        self.results["css_list"] = css_list
        return len(css_summaries), errors

    def _get_css_detail(self, css_name: str) -> dict[str, Any] | None:
        """Fetch full CSS detail and normalize member ordering.

        CRITICAL: CSS member ordering determines partition priority.
        The ``index`` field on each member defines the evaluation order.
        Members are sorted by index to preserve correct ordering.
        """
        try:
            detail = self.get_detail("getCss", name=css_name)
        except Exception as exc:
            logger.warning("[%s] getCss error for %s: %s", self.name, css_name, exc)
            return None

        if detail is None:
            return None

        # Normalize members — may be None, empty dict, or populated
        raw_members = detail.get("members")
        member_entries = to_list(raw_members, "member")

        # Sort by index to preserve partition evaluation order
        sorted_members = sorted(
            member_entries,
            key=lambda m: int(m.get("index", 0)) if isinstance(m, dict) else 0,
        )

        detail["members"] = sorted_members
        return detail

    # ------------------------------------------------------------------
    # Route Patterns — list only (no get needed)
    # ------------------------------------------------------------------

    def _extract_route_patterns(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing route patterns...", self.name)
        patterns = self.paginated_list(
            method_name="listRoutePattern",
            search_criteria={"pattern": "%"},
            returned_tags=ROUTE_PATTERN_RETURNED_TAGS,
        )
        self.results["route_patterns"] = patterns
        logger.info("[%s] Found %d route patterns", self.name, len(patterns))
        return len(patterns), []

    # ------------------------------------------------------------------
    # Gateways — list + get (devicePoolName requires getGateway)
    # Verified: listGateway search criteria is domainName
    # ------------------------------------------------------------------

    def _extract_gateways(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing gateways...", self.name)
        gw_summaries = self.paginated_list(
            method_name="listGateway",
            search_criteria={"domainName": "%"},
            returned_tags=GATEWAY_RETURNED_TAGS,
        )
        logger.info("[%s] Found %d gateways", self.name, len(gw_summaries))

        gateways: list[dict[str, Any]] = []
        errors: list[str] = []
        for summary in gw_summaries:
            gw_name = ref_value(summary.get("domainName")) or summary.get("domainName")
            if not gw_name:
                errors.append("Gateway with no domainName in listGateway result")
                continue
            try:
                detail = self.get_detail("getGateway", domainName=gw_name)
            except Exception as exc:
                logger.warning("[%s] getGateway error for %s: %s", self.name, gw_name, exc)
                errors.append(f"getGateway failed for {gw_name}")
                # Fall back to summary (no devicePoolName)
                gateways.append(summary)
                continue
            if detail is None:
                gateways.append(summary)
                continue
            gateways.append(detail)

        self.results["gateways"] = gateways
        return len(gw_summaries), errors

    # ------------------------------------------------------------------
    # SIP Trunks — list + get (destinations require getSipTrunk)
    # Verified: listSipTrunk method confirmed on live CUCM 15.0
    # ------------------------------------------------------------------

    def _extract_sip_trunks(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing SIP trunks...", self.name)
        trunk_summaries = self.paginated_list(
            method_name="listSipTrunk",
            search_criteria={"name": "%"},
            returned_tags=SIP_TRUNK_LIST_RETURNED_TAGS,
        )
        logger.info("[%s] Found %d SIP trunks", self.name, len(trunk_summaries))

        # getSipTrunk for full detail including destinations array
        trunks: list[dict[str, Any]] = []
        errors: list[str] = []
        for summary in trunk_summaries:
            trunk_name = ref_value(summary.get("name")) or summary.get("name")
            if not trunk_name:
                errors.append("SIP trunk with no name in listSipTrunk result")
                continue
            try:
                detail = self.get_detail("getSipTrunk", name=trunk_name)
            except Exception as exc:
                logger.warning("[%s] getSipTrunk error for %s: %s", self.name, trunk_name, exc)
                errors.append(f"getSipTrunk failed for {trunk_name}")
                trunks.append(summary)
                continue
            if detail is None:
                trunks.append(summary)
                continue
            # Normalize destinations list
            raw_dest = detail.get("destinations") if hasattr(detail, "get") else None
            if raw_dest:
                detail["destinations"] = to_list(raw_dest, "destination")
            trunks.append(detail)

        self.results["sip_trunks"] = trunks
        return len(trunk_summaries), errors

    # ------------------------------------------------------------------
    # Route Groups — list + get for member trunks
    # ------------------------------------------------------------------

    def _extract_route_groups(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing route groups...", self.name)
        rg_summaries = self.paginated_list(
            method_name="listRouteGroup",
            search_criteria={"name": "%"},
            returned_tags=ROUTE_GROUP_LIST_RETURNED_TAGS,
        )
        logger.info("[%s] Found %d route groups", self.name, len(rg_summaries))

        route_groups: list[dict[str, Any]] = []
        errors: list[str] = []
        for summary in rg_summaries:
            rg_name = ref_value(summary.get("name")) or summary.get("name")
            if not rg_name:
                errors.append("Route group with no name in listRouteGroup result")
                continue

            try:
                detail = self.get_detail("getRouteGroup", name=rg_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getRouteGroup error for %s: %s", self.name, rg_name, exc,
                )
                errors.append(f"getRouteGroup failed for {rg_name}")
                continue

            if detail is None:
                errors.append(f"getRouteGroup returned None for {rg_name}")
                continue

            # Normalize members
            raw_members = detail.get("members")
            detail["members"] = to_list(raw_members, "member")
            route_groups.append(detail)

        self.results["route_groups"] = route_groups
        return len(rg_summaries), errors

    # ------------------------------------------------------------------
    # Route Lists — list + get for member route groups
    # ------------------------------------------------------------------

    def _extract_route_lists(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing route lists...", self.name)
        rl_summaries = self.paginated_list(
            method_name="listRouteList",
            search_criteria={"name": "%"},
            returned_tags=ROUTE_LIST_LIST_RETURNED_TAGS,
        )
        logger.info("[%s] Found %d route lists", self.name, len(rl_summaries))

        route_lists: list[dict[str, Any]] = []
        errors: list[str] = []
        for summary in rl_summaries:
            rl_name = ref_value(summary.get("name")) or summary.get("name")
            if not rl_name:
                errors.append("Route list with no name in listRouteList result")
                continue

            try:
                detail = self.get_detail("getRouteList", name=rl_name)
            except Exception as exc:
                logger.warning(
                    "[%s] getRouteList error for %s: %s", self.name, rl_name, exc,
                )
                errors.append(f"getRouteList failed for {rl_name}")
                continue

            if detail is None:
                errors.append(f"getRouteList returned None for {rl_name}")
                continue

            # Normalize members
            raw_members = detail.get("members")
            detail["members"] = to_list(raw_members, "member")
            route_lists.append(detail)

        self.results["route_lists"] = route_lists
        return len(rl_summaries), errors

    # ------------------------------------------------------------------
    # Translation Patterns — list only (no get needed)
    # ------------------------------------------------------------------

    def _extract_translation_patterns(self) -> tuple[int, list[str]]:
        logger.info("[%s] Listing translation patterns...", self.name)
        patterns = self.paginated_list(
            method_name="listTransPattern",
            search_criteria={"pattern": "%"},
            returned_tags=TRANSLATION_PATTERN_RETURNED_TAGS,
        )
        self.results["translation_patterns"] = patterns
        logger.info("[%s] Found %d translation patterns", self.name, len(patterns))
        return len(patterns), []
