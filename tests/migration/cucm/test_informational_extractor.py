"""Tests for InformationalExtractor — Tier 3 informational object types."""
from unittest.mock import MagicMock

import pytest

from wxcli.migration.cucm.extractors.informational import (
    INFORMATIONAL_TYPES,
    InformationalExtractor,
)


def _mock_connection(list_results=None, sql_results=None, get_results=None):
    """Build a mock AXLConnection for informational extraction.

    list_results: dict mapping method_name -> list of dicts
    sql_results: dict mapping query substring -> list of dicts
    get_results: dict mapping method_name -> dict
    """
    conn = MagicMock()
    list_results = list_results or {}
    sql_results = sql_results or {}
    get_results = get_results or {}

    def paginated_list(method_name, search_criteria, returned_tags, page_size):
        return list_results.get(method_name, [])

    conn.paginated_list = MagicMock(side_effect=paginated_list)

    def execute_sql(query):
        for substring, rows in sql_results.items():
            if substring in query:
                return rows
        return []

    conn.execute_sql = MagicMock(side_effect=execute_sql)

    def get_detail(method_name, **kwargs):
        return get_results.get(method_name)

    conn.get_detail = MagicMock(side_effect=get_detail)

    # For getEnterprise (service call, not get_detail)
    conn.service = MagicMock()
    if "getEnterprise" in get_results:
        conn.service.getEnterprise.return_value = get_results["getEnterprise"]
    else:
        conn.service.getEnterprise.return_value = None

    return conn


class TestInformationalExtractorStandardTypes:
    """Test the 16 standard AXL list types."""

    def test_extracts_regions(self):
        conn = _mock_connection(list_results={
            "listRegion": [
                {"name": "Default", "defaultCodec": "G.711"},
                {"name": "LowBandwidth", "defaultCodec": "G.729"},
            ],
        })
        ext = InformationalExtractor(conn)
        result = ext.extract()
        regions = ext.results.get("region", [])
        assert len(regions) == 2
        assert regions[0]["name"] == "Default"
        assert result.total >= 2

    def test_extracts_srst_references(self):
        conn = _mock_connection(list_results={
            "listSrst": [{"name": "SRST-HQ", "ipAddress": "10.1.1.1", "port": "2000"}],
        })
        ext = InformationalExtractor(conn)
        ext.extract()
        assert len(ext.results.get("srst", [])) == 1

    def test_extracts_app_users(self):
        conn = _mock_connection(list_results={
            "listAppUser": [
                {"userid": "CUCXNSvc", "description": "CUC Service", "associatedDevices": ""},
                {"userid": "JTAPI_USER", "description": "JTAPI for Finesse", "associatedDevices": "CTI-1"},
            ],
        })
        ext = InformationalExtractor(conn)
        ext.extract()
        app_users = ext.results.get("app_user", [])
        assert len(app_users) == 2
        assert app_users[1]["userid"] == "JTAPI_USER"

    def test_empty_cluster_returns_zero_counts(self):
        conn = _mock_connection()  # all empty
        ext = InformationalExtractor(conn)
        result = ext.extract()
        assert result.failed == 0
        total_objects = sum(len(v) for v in ext.results.values())
        assert total_objects == 0

    def test_failed_list_records_error_not_crash(self):
        conn = _mock_connection()
        conn.paginated_list.side_effect = Exception("AXL timeout")
        ext = InformationalExtractor(conn)
        result = ext.extract()
        assert result.failed > 0
        assert any("timeout" in e.lower() for e in result.errors)


class TestInformationalExtractorSQL:
    """Test SQL-based extraction (softkey templates, intercom)."""

    def test_extracts_softkey_templates_via_sql(self):
        conn = _mock_connection(sql_results={
            "softkeytemplate": [
                {"name": "Standard", "description": "Default softkey template"},
                {"name": "Custom-Sales", "description": "Sales team layout"},
            ],
        })
        ext = InformationalExtractor(conn)
        ext.extract()
        sk = ext.results.get("softkey_template", [])
        assert len(sk) == 2
        assert sk[0]["name"] == "Standard"
        assert sk[0]["_category"] == "not_migratable"

    def test_extracts_intercom_dns_via_sql(self):
        conn = _mock_connection(sql_results={
            "numplan": [
                {"dnorpattern": "9001", "description": "Lobby intercom", "fkroutepartition": "pk-1"},
            ],
        })
        ext = InformationalExtractor(conn)
        ext.extract()
        intercom = ext.results.get("intercom", [])
        assert len(intercom) == 1
        assert intercom[0]["dnorpattern"] == "9001"

    def test_sql_failure_records_error_not_crash(self):
        conn = _mock_connection()
        conn.execute_sql.side_effect = Exception("SQL error")
        ext = InformationalExtractor(conn)
        result = ext.extract()
        assert any("SQL" in e for e in result.errors)


class TestInformationalExtractorEnterprise:
    """Test enterprise params and service params."""

    def test_extracts_enterprise_params(self):
        conn = _mock_connection()
        from unittest.mock import patch
        mock_params = {"clusterName": "CUCM-LAB", "clusterDescription": "Lab cluster"}
        conn.service.getEnterprise.return_value = mock_params
        with patch(
            "zeep.helpers.serialize_object",
            return_value=mock_params,
        ):
            ext = InformationalExtractor(conn)
            ext.extract()
        ep = ext.results.get("enterprise_params", [])
        assert len(ep) == 1
        assert ep[0]["_category"] == "planning"

    def test_extracts_service_params_filtered(self):
        conn = _mock_connection(list_results={
            "listProcessConfig": [
                {"name": "MaxCallDuration", "service": "Cisco CallManager", "value": "720"},
                {"name": "SomeWebParam", "service": "Cisco Tomcat", "value": "true"},
                {"name": "TFTPMaxThreads", "service": "Cisco TFTP", "value": "50"},
            ],
        })
        ext = InformationalExtractor(conn)
        ext.extract()
        sp = ext.results.get("service_params", [])
        # Should filter to telephony-related: CallManager and TFTP, not Tomcat
        assert len(sp) == 2
        services = [s.get("service") for s in sp]
        assert "Cisco CallManager" in services
        assert "Cisco TFTP" in services
        assert "Cisco Tomcat" not in services


class TestInformationalTypes:
    """Test the INFORMATIONAL_TYPES constant."""

    def test_has_16_standard_types(self):
        assert len(INFORMATIONAL_TYPES) == 16

    def test_all_categories_present(self):
        categories = {t[4] for t in INFORMATIONAL_TYPES}
        assert categories == {"cloud_managed", "not_migratable", "different_arch", "planning"}

    def test_all_suffixes_unique(self):
        suffixes = [t[0] for t in INFORMATIONAL_TYPES]
        assert len(suffixes) == len(set(suffixes))


from wxcli.migration.models import MigrationObject, MigrationStatus
from wxcli.migration.transform.normalizers import NORMALIZER_REGISTRY, RAW_DATA_MAPPING


class TestInformationalNormalizer:
    """Test the informational normalizer pass-through."""

    def test_normalizer_registered_for_all_info_types(self):
        info_suffixes = [
            "region", "srst", "media_resource_group", "media_resource_list",
            "aar_group", "device_mobility_group", "conference_bridge",
            "softkey_template", "ip_phone_service", "intercom",
            "common_phone_config", "phone_button_template",
            "feature_control_policy", "credential_policy",
            "recording_profile", "ldap_directory",
            "app_user", "h323_gateway", "enterprise_params", "service_params",
        ]
        for suffix in info_suffixes:
            key = f"info_{suffix}"
            assert key in NORMALIZER_REGISTRY, f"Missing normalizer for {key}"

    def test_raw_data_mapping_entries_for_info_types(self):
        info_entries = [
            (ext, sub, norm) for ext, sub, norm in RAW_DATA_MAPPING
            if ext == "informational"
        ]
        assert len(info_entries) == 20

    def test_normalizer_produces_migration_object(self):
        normalizer = NORMALIZER_REGISTRY["info_region"]
        item = {"name": "Default", "defaultCodec": "G.711", "_category": "cloud_managed", "_info_type": "region"}
        obj = normalizer(item, cluster="test-cluster")
        assert isinstance(obj, MigrationObject)
        assert obj.canonical_id == "info_region:Default"
        assert obj.status == MigrationStatus.NORMALIZED
        assert obj.pre_migration_state["name"] == "Default"
        assert obj.pre_migration_state["_category"] == "cloud_managed"
        assert obj.provenance.source_system == "cucm"
        assert obj.provenance.cluster == "test-cluster"

    def test_normalizer_uses_userid_for_app_users(self):
        normalizer = NORMALIZER_REGISTRY["info_app_user"]
        item = {"userid": "JTAPI_USER", "description": "JTAPI", "_category": "planning", "_info_type": "app_user"}
        obj = normalizer(item, cluster="default")
        assert obj.canonical_id == "info_app_user:JTAPI_USER"

    def test_normalizer_uses_dnorpattern_for_intercom(self):
        normalizer = NORMALIZER_REGISTRY["info_intercom"]
        item = {"dnorpattern": "9001", "_category": "not_migratable", "_info_type": "intercom"}
        obj = normalizer(item, cluster="default")
        assert obj.canonical_id == "info_intercom:9001"

    def test_normalizer_skips_items_without_name(self):
        normalizer = NORMALIZER_REGISTRY["info_region"]
        item = {"defaultCodec": "G.711", "_category": "cloud_managed"}
        obj = normalizer(item, cluster="default")
        assert obj is None
