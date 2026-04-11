"""Tests for Tier 4 intercept candidate extraction."""
from unittest.mock import MagicMock

from wxcli.migration.cucm.extractors.tier4 import Tier4Extractor


def _make_extractor():
    conn = MagicMock()
    conn.paginated_list.return_value = []  # stub other extractions
    conn.execute_sql.return_value = []
    return Tier4Extractor(conn), conn


class TestExtractInterceptCandidates:
    def test_extract_blocked_partition_candidates(self):
        """DNs in partitions named like '%intercept%' or '%block%' are detected."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [
            [{"dnorpattern": "1001", "partition_name": "Blocked_PT", "userid": "jsmith"}],
            [],
        ]
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 1
        assert candidates[0]["dn"] == "1001"
        assert candidates[0]["partition"] == "Blocked_PT"
        assert candidates[0]["signal_type"] == "blocked_partition"
        assert candidates[0]["userid"] == "jsmith"

    def test_extract_cfa_voicemail_candidates(self):
        """Users with CFA to voicemail + no device are detected."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [
            [],
            [{"dnorpattern": "2001", "partition_name": "Internal_PT",
              "cfadestination": "+14155550000", "userid": "jdoe"}],
        ]
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 1
        assert candidates[0]["signal_type"] == "cfa_voicemail"
        assert candidates[0]["forward_destination"] == "+14155550000"

    def test_extract_no_candidates(self):
        """Clean environment produces empty list."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [[], []]
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 0

    def test_partition_name_matching(self):
        """Various partition naming conventions are detected."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [
            [
                {"dnorpattern": "1001", "partition_name": "Intercept_PT", "userid": "u1"},
                {"dnorpattern": "1002", "partition_name": "OOS_PT", "userid": "u2"},
                {"dnorpattern": "1003", "partition_name": "out_of_service_PT", "userid": "u3"},
            ],
            [],
        ]
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 3
        assert all(c["signal_type"] == "blocked_partition" for c in candidates)

    def test_sql_failure_returns_empty(self):
        """SQL query failure logs warning, returns empty list."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = Exception("connection lost")
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 0
        assert any("intercept" in e.lower() for e in result.errors)

    def test_deduplicates_across_queries(self):
        """Same DN appearing in both queries is not duplicated."""
        ext, conn = _make_extractor()
        conn.execute_sql.side_effect = [
            [{"dnorpattern": "1001", "partition_name": "Blocked_PT", "userid": "jsmith"}],
            [{"dnorpattern": "1001", "partition_name": "Blocked_PT",
              "cfadestination": "+14155550000", "userid": "jsmith"}],
        ]
        result = ext.extract()
        candidates = ext.results.get("intercept_candidates", [])
        assert len(candidates) == 1
        assert candidates[0]["signal_type"] == "blocked_partition"
