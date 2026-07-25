"""Tests for executive/assistant extraction from CUCM."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from wxcli.migration.cucm.extractors.features import (
    EXEC_ASSISTANT_TABLES,
    EXEC_SETTINGS_TABLES,
    FeatureExtractor,
    _is_missing_table,
)
from wxcli.migration.models import (
    CanonicalExecutiveAssistant,
    MigrationStatus,
    Provenance,
)

ALL_EXEC_TABLES = tuple(sorted(set(EXEC_ASSISTANT_TABLES) | set(EXEC_SETTINGS_TABLES)))


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


def _make_extractor(
    sql_pairs=None,
    sql_settings=None,
    raise_on_sql=False,
    existing_tables=ALL_EXEC_TABLES,
    probe_raises=False,
    missing_table_fault=False,
):
    """Build a FeatureExtractor with mocked connection.

    ``existing_tables`` drives the systables probe; ``probe_raises`` makes the
    probe itself fail; ``missing_table_fault`` makes the executive/assistant
    queries raise the CUCM missing-table SOAP fault.
    """
    mock_conn = MagicMock()
    mock_conn.paginated_list.return_value = []
    mock_conn.get_detail.return_value = None
    mock_conn.version = "14.0"

    pairs = sql_pairs or []
    settings = sql_settings or []

    def sql_side_effect(query):
        ql = query.lower()
        if "systables" in ql:
            if probe_raises:
                raise Exception("systables unreadable")
            return [{"tabname": t} for t in existing_tables]
        if raise_on_sql:
            raise Exception("SQL table not found")
        if "executiveassistant" in ql:
            if missing_table_fault:
                raise Exception(
                    "The specified table (executiveassistant) is not in the database."
                )
            return pairs
        if "subscribedservice" in ql:
            if missing_table_fault:
                raise Exception(
                    "The specified table (endusersubscribedservice) is not in "
                    "the database."
                )
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


def _exec_notes(result):
    """Notes mentioning the executive/assistant queries."""
    return [e for e in result.errors if "SQL query" in e]


class TestIsMissingTable:
    def test_matches_cucm_missing_table_fault(self):
        exc = Exception(
            "The specified table (executiveassistant) is not in the database."
        )
        assert _is_missing_table(exc) is True

    def test_does_not_match_unsupported_operation_fault(self):
        """The A3/A4 marker must NOT be classified as a missing table."""
        assert _is_missing_table(Exception("Service has no operation 'x'")) is False

    def test_does_not_match_generic_failure(self):
        assert _is_missing_table(Exception("connection reset by peer")) is False


class TestMissingTableClassifiedUnsupported:
    def test_missing_table_fault_is_unsupported_not_error(self):
        """A raised missing-table fault is recorded as unsupported, not failed."""
        ext = _make_extractor(missing_table_fault=True, probe_raises=True)
        result = ext.extract()

        notes = _exec_notes(result)
        assert len(notes) == 2
        assert all("unsupported on this CUCM schema" in n for n in notes)
        assert all(n.endswith("— skipped") for n in notes)
        assert all("failed:" not in n for n in notes)
        assert result.failed == 0
        assert ext.results["executive_assistant_pairs"] == []
        assert ext.results["executive_settings"] == []

    def test_probe_absence_skips_before_querying(self):
        """When systables says the tables are absent, the joins never run."""
        ext = _make_extractor(existing_tables=())
        result = ext.extract()

        notes = _exec_notes(result)
        assert len(notes) == 2
        assert any("missing table(s): executiveassistant" in n for n in notes)
        assert any(
            "missing table(s): endusersubscribedservice, subscribedservice" in n
            for n in notes
        )
        assert result.failed == 0

        queries = [c.args[0] for c in ext.conn.execute_sql.call_args_list]
        assert sum("systables" in q for q in queries) == 1
        assert not any("JOIN enduser exec_user" in q for q in queries)

    def test_partial_absence_only_skips_affected_query(self):
        """executiveassistant present but subscription tables absent."""
        ext = _make_extractor(
            sql_pairs=[{"executive_userid": "jsmith", "assistant_userid": "jdoe"}],
            existing_tables=("executiveassistant",),
        )
        result = ext.extract()

        assert len(ext.results["executive_assistant_pairs"]) == 1
        assert ext.results["executive_settings"] == []
        notes = _exec_notes(result)
        assert len(notes) == 1
        assert "executive settings SQL query unsupported" in notes[0]

    def test_generic_sql_failure_still_reported_as_error(self):
        """Non-missing-table failures keep the existing error wording."""
        ext = _make_extractor(raise_on_sql=True)
        result = ext.extract()

        notes = _exec_notes(result)
        assert len(notes) == 2
        assert all("failed: SQL table not found" in n for n in notes)
        assert not any("unsupported" in n for n in notes)


class TestTablesPresentBehaviourUnchanged:
    def test_probe_runs_once_and_queries_proceed(self):
        ext = _make_extractor(
            sql_pairs=[{"executive_userid": "jsmith", "assistant_userid": "jdoe"}],
            sql_settings=[{"userid": "jsmith", "service_name": "Executive"}],
        )
        result = ext.extract()

        assert len(ext.results["executive_assistant_pairs"]) == 1
        assert len(ext.results["executive_settings"]) == 1
        assert _exec_notes(result) == []

        queries = [c.args[0] for c in ext.conn.execute_sql.call_args_list]
        assert sum("systables" in q for q in queries) == 1

    def test_unreadable_probe_falls_through_to_the_query(self):
        """An unreadable probe is not evidence a table is absent."""
        ext = _make_extractor(
            sql_pairs=[{"executive_userid": "jsmith", "assistant_userid": "jdoe"}],
            sql_settings=[{"userid": "jsmith", "service_name": "Executive"}],
            probe_raises=True,
        )
        result = ext.extract()

        assert len(ext.results["executive_assistant_pairs"]) == 1
        assert len(ext.results["executive_settings"]) == 1
        assert _exec_notes(result) == []
