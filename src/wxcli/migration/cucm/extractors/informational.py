"""Tier 3: Informational extraction — CUCM objects with no Webex equivalent.

Extracted for assessment report only. No canonical types, no mappers.
Objects stored as MigrationObject with object_type="info_{type_name}".

20 types across 4 categories:
- cloud_managed (7): Regions, SRST, MRG, MRL, AAR, Device Mobility, Conference Bridges
- not_migratable (3): Softkey Templates, IP Phone Services, Intercom DNs
- different_arch (6): Common Phone Config, Phone Button Templates, Feature Control,
                      Credential Policies, Recording Profiles, LDAP Directories
- planning (4): Application Users, H.323 Gateways, Enterprise Params, Service Params
"""

from __future__ import annotations

import logging
from typing import Any

from wxcli.migration.cucm.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# (suffix, axl_list_method, search_criteria, returned_tags, category)
# These 16 types use standard paginated_list().
INFORMATIONAL_TYPES: list[tuple[str, str, dict, dict, str]] = [
    # Category 1: Cloud-managed
    ("region", "listRegion", {"name": "%"}, {"name": "", "defaultCodec": ""}, "cloud_managed"),
    ("srst", "listSrst", {"name": "%"}, {"name": "", "ipAddress": "", "port": ""}, "cloud_managed"),
    ("media_resource_group", "listMediaResourceGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("media_resource_list", "listMediaResourceList", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("aar_group", "listAarGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("device_mobility_group", "listDeviceMobilityGroup", {"name": "%"}, {"name": "", "description": ""}, "cloud_managed"),
    ("conference_bridge", "listConferenceBridge", {"name": "%"}, {"name": "", "description": "", "product": ""}, "cloud_managed"),
    # Category 2: Not migratable
    ("ip_phone_service", "listIpPhoneService", {"name": "%"}, {"name": "", "url": "", "serviceType": ""}, "not_migratable"),
    # Category 3: Different architecture
    ("common_phone_config", "listCommonPhoneConfig", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("phone_button_template", "listPhoneButtonTemplate", {"name": "%"}, {"name": ""}, "different_arch"),
    ("feature_control_policy", "listFeatureControlPolicy", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("credential_policy", "listCredentialPolicy", {"name": "%"}, {"name": "", "description": ""}, "different_arch"),
    ("recording_profile", "listRecordingProfile", {"name": "%"}, {"name": "", "recorderDestination": ""}, "different_arch"),
    ("ldap_directory", "listLdapDirectory", {"name": "%"}, {"name": "", "ldapDn": ""}, "different_arch"),
    # Category 4: Planning input
    ("app_user", "listAppUser", {"userid": "%"}, {"userid": "", "description": "", "associatedDevices": ""}, "planning"),
    ("h323_gateway", "listH323Gateway", {"name": "%"}, {"name": "", "description": "", "product": ""}, "planning"),
]

# Category metadata for report rendering
CATEGORY_METADATA: dict[str, dict[str, str]] = {
    "cloud_managed": {
        "label": "Cloud-Managed Resources",
        "message": "No migration action needed — Webex manages this automatically.",
    },
    "not_migratable": {
        "label": "Feature Gaps",
        "message": "This CUCM feature has no Webex equivalent — functionality will be lost.",
    },
    "different_arch": {
        "label": "Manual Reconfiguration Required",
        "message": "Must be reconfigured manually in Webex Control Hub.",
    },
    "planning": {
        "label": "Migration Planning Inputs",
        "message": "Data informing migration planning decisions.",
    },
}

# Friendly display names for each info type
DISPLAY_NAMES: dict[str, str] = {
    "region": "Regions",
    "srst": "SRST References",
    "media_resource_group": "Media Resource Groups",
    "media_resource_list": "Media Resource Lists",
    "aar_group": "AAR Groups",
    "device_mobility_group": "Device Mobility Groups",
    "conference_bridge": "Conference Bridges",
    "softkey_template": "Softkey Templates",
    "ip_phone_service": "IP Phone Services",
    "intercom": "Intercom DNs",
    "common_phone_config": "Common Phone Profiles",
    "phone_button_template": "Phone Button Templates",
    "feature_control_policy": "Feature Control Policies",
    "credential_policy": "Credential Policies",
    "recording_profile": "Recording Profiles",
    "ldap_directory": "LDAP Directories",
    "app_user": "Application Users",
    "h323_gateway": "H.323 Gateways",
    "enterprise_params": "Enterprise Parameters",
    "service_params": "Service Parameters",
}

# Webex equivalents for "different_arch" types
WEBEX_EQUIVALENTS: dict[str, str] = {
    "common_phone_config": "Device configuration templates",
    "phone_button_template": "Line key templates",
    "feature_control_policy": "Calling policies (org/location level)",
    "credential_policy": "SSO / password policies",
    "recording_profile": "Call recording settings",
    "ldap_directory": "Directory sync (Azure AD / Okta / SCIM)",
}

# Workarounds for "not_migratable" types
NOT_MIGRATABLE_WORKAROUNDS: dict[str, str] = {
    "softkey_template": "9800-series supports PSK; classic MPP uses Webex defaults",
    "ip_phone_service": "Webex app replaces most XML service use cases",
    "intercom": "Speed dial + auto-answer as workaround",
}


class InformationalExtractor(BaseExtractor):
    """Extract 20 CUCM object types for assessment report only.

    No canonical types, no mappers, no execution handlers.
    Data flows: extractor -> store -> report appendix.
    """

    name = "informational"

    def __init__(self, connection) -> None:
        super().__init__(connection)
        self.results: dict[str, list[dict[str, Any]]] = {}

    def extract(self) -> ExtractionResult:
        """Run extraction for all 20 informational types."""
        result = ExtractionResult(extractor=self.name)

        # 1. Standard AXL list types (16 types)
        for suffix, method, criteria, tags, category in INFORMATIONAL_TYPES:
            items = self._extract_list_type(suffix, method, criteria, tags, category, result)
            self.results[suffix] = items

        # 2. Softkey templates via SQL (AXL list doesn't exist)
        self.results["softkey_template"] = self._extract_softkey_templates(result)

        # 3. Intercom DNs via SQL
        self.results["intercom"] = self._extract_intercom_dns(result)

        # 4. Enterprise parameters (single getEnterprise call)
        self.results["enterprise_params"] = self._extract_enterprise_params(result)

        # 5. Service parameters (filtered listProcessConfig)
        self.results["service_params"] = self._extract_service_params(result)

        logger.info(
            "[%s] Extracted %d informational objects across %d types (%d failed)",
            self.name,
            result.total,
            sum(1 for v in self.results.values() if v),
            result.failed,
        )
        return result

    def _extract_list_type(
        self,
        suffix: str,
        method: str,
        criteria: dict,
        tags: dict,
        category: str,
        result: ExtractionResult,
    ) -> list[dict[str, Any]]:
        """Extract a single AXL list type."""
        try:
            items = self.paginated_list(method, criteria, tags)
        except Exception as exc:
            logger.warning("[%s] %s failed: %s", self.name, method, exc)
            result.errors.append(f"{method} failed: {exc}")
            result.failed += 1
            return []

        result.total += len(items)
        for item in items:
            item["_category"] = category
            item["_info_type"] = suffix
        return items

    def _extract_softkey_templates(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract softkey template names via SQL (AXL list doesn't exist in CUCM 15.0)."""
        try:
            rows = self.conn.execute_sql(
                "SELECT name, description FROM softkeytemplate ORDER BY name"
            )
        except Exception as exc:
            logger.warning("[%s] Softkey template SQL failed: %s", self.name, exc)
            result.errors.append(f"Softkey template SQL failed: {exc}")
            return []

        result.total += len(rows)
        for row in rows:
            row["_category"] = "not_migratable"
            row["_info_type"] = "softkey_template"
        return rows

    def _extract_intercom_dns(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract intercom DNs via SQL query."""
        try:
            rows = self.conn.execute_sql(
                "SELECT dnorpattern, description, fkroutepartition "
                "FROM numplan WHERE tkpatternusage = 9 ORDER BY dnorpattern"
            )
        except Exception as exc:
            logger.warning("[%s] Intercom DN SQL failed: %s", self.name, exc)
            result.errors.append(f"Intercom DN SQL failed: {exc}")
            return []

        result.total += len(rows)
        for row in rows:
            row["_category"] = "not_migratable"
            row["_info_type"] = "intercom"
        return rows

    def _extract_enterprise_params(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract enterprise parameters via single getEnterprise call."""
        try:
            raw = self.conn.service.getEnterprise()
            if raw is None:
                return []
            from zeep.helpers import serialize_object
            params = serialize_object(raw, dict)
            if not isinstance(params, dict):
                params = {"raw": str(params)}
        except Exception as exc:
            logger.warning("[%s] getEnterprise failed: %s", self.name, exc)
            result.errors.append(f"getEnterprise failed: {exc}")
            return []

        result.total += 1
        params["_category"] = "planning"
        params["_info_type"] = "enterprise_params"
        params["name"] = "Enterprise Parameters"
        return [params]

    def _extract_service_params(self, result: ExtractionResult) -> list[dict[str, Any]]:
        """Extract telephony-related service parameters via listProcessConfig."""
        try:
            items = self.paginated_list(
                "listProcessConfig",
                {"name": "%"},
                {"name": "", "service": "", "value": ""},
            )
        except Exception as exc:
            logger.warning("[%s] listProcessConfig failed: %s", self.name, exc)
            result.errors.append(f"listProcessConfig failed: {exc}")
            return []

        telephony_keywords = (
            "callmanager", "telephony", "tftp", "certificate",
            "cisco call", "cisco ip voice",
        )
        filtered = []
        for item in items:
            service = (item.get("service") or "").lower()
            if any(kw in service for kw in telephony_keywords):
                item["_category"] = "planning"
                item["_info_type"] = "service_params"
                filtered.append(item)

        result.total += len(filtered)
        return filtered
