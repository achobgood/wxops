"""Tests for executive/assistant extraction from CUCM."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from wxcli.migration.cucm.extractors.features import FeatureExtractor
from wxcli.migration.models import (
    CanonicalExecutiveAssistant,
    MigrationStatus,
    Provenance,
)


class TestCanonicalExecutiveAssistantModel:
    def test_model_fields(self):
        obj = CanonicalExecutiveAssistant(
            canonical_id="executive_assistant:jsmith",
            provenance=Provenance(
                source_system="cucm",
                source_id="test",
                source_name="test",
                extracted_at=datetime.now(timezone.utc),
            ),
            status=MigrationStatus.ANALYZED,
            executive_canonical_id="user:jsmith",
            assistant_canonical_ids=["user:jdoe", "user:asmith"],
            alerting_mode="SIMULTANEOUS",
            filter_enabled=True,
            filter_type="ALL_CALLS",
            screening_enabled=True,
        )
        assert obj.executive_canonical_id == "user:jsmith"
        assert len(obj.assistant_canonical_ids) == 2
        assert obj.alerting_mode == "SIMULTANEOUS"
        assert obj.filter_enabled is True
        assert obj.filter_type == "ALL_CALLS"
        assert obj.screening_enabled is True

    def test_model_defaults(self):
        obj = CanonicalExecutiveAssistant(
            canonical_id="executive_assistant:boss",
            provenance=Provenance(
                source_system="cucm",
                source_id="test",
                source_name="test",
                extracted_at=datetime.now(timezone.utc),
            ),
        )
        assert obj.alerting_mode == "SIMULTANEOUS"
        assert obj.filter_enabled is False
        assert obj.filter_type == "ALL_CALLS"
        assert obj.screening_enabled is False
        assert obj.assistant_canonical_ids == []


def _make_extractor(sql_pairs=None, sql_settings=None, raise_on_sql=False):
    """Build a FeatureExtractor with mocked connection."""
    mock_conn = MagicMock()
    mock_conn.paginated_list.return_value = []
    mock_conn.get_detail.return_value = None

    pairs = sql_pairs or []
    settings = sql_settings or []

    def sql_side_effect(query):
        if raise_on_sql:
            raise Exception("SQL table not found")
        ql = query.lower()
        if "executiveassistant" in ql:
            return pairs
        if "subscribedservice" in ql:
            return settings
        return []

    mock_conn.execute_sql.side_effect = sql_side_effect
    return FeatureExtractor(mock_conn)


class TestExtractExecutiveAssistantPairs:
    def test_extract_pairs_basic(self):
        pairs = [
            {
                "executive_userid": "jsmith",
                "assistant_userid": "jdoe",
                "executive_pkid": "{EXEC-1}",
                "assistant_pkid": "{ASST-1}",
            },
            {
                "executive_userid": "jsmith",
                "assistant_userid": "asmith",
                "executive_pkid": "{EXEC-1}",
                "assistant_pkid": "{ASST-2}",
            },
        ]
        ext = _make_extractor(sql_pairs=pairs)
        ext.extract()

        assert "executive_assistant_pairs" in ext.results
        assert len(ext.results["executive_assistant_pairs"]) == 2
        assert ext.results["executive_assistant_pairs"][0]["executive_userid"] == "jsmith"
        assert ext.results["executive_assistant_pairs"][1]["assistant_userid"] == "asmith"

    def test_extract_pairs_empty(self):
        ext = _make_extractor(sql_pairs=[])
        ext.extract()
        assert ext.results.get("executive_assistant_pairs", []) == []


class TestExtractExecutiveSettings:
    def test_extract_settings_executive(self):
        settings = [
            {
                "userid": "jsmith",
                "service_name": "Executive",
                "servicetype": "1",
            },
        ]
        ext = _make_extractor(sql_settings=settings)
        ext.extract()

        assert "executive_settings" in ext.results
        assert len(ext.results["executive_settings"]) == 1
        assert ext.results["executive_settings"][0]["userid"] == "jsmith"
        assert ext.results["executive_settings"][0]["service_name"] == "Executive"

    def test_extract_settings_assistant(self):
        settings = [
            {
                "userid": "jdoe",
                "service_name": "Executive-Assistant",
                "servicetype": "2",
            },
        ]
        ext = _make_extractor(sql_settings=settings)
        ext.extract()

        assert len(ext.results["executive_settings"]) == 1
        assert ext.results["executive_settings"][0]["service_name"] == "Executive-Assistant"


class TestExtractSQLErrorGraceful:
    def test_extract_sql_error_graceful(self):
        """SQL failure should not crash — returns empty lists with errors."""
        ext = _make_extractor(raise_on_sql=True)
        result = ext.extract()

        assert ext.results.get("executive_assistant_pairs", []) == []
        assert ext.results.get("executive_settings", []) == []
        assert len(result.errors) >= 2
