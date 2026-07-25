"""Tests for MOHExtractor — Music on Hold audio sources.

Field names and the getMohAudioSource key are pinned to the AXL 14.0/15.0
schema: LMohAudioSource exposes <sourceFile> (not <sourceFileName>) and has no
<isDefault>; GetMohAudioSourceReq keys on sourceId or uuid, never name.
"""
from unittest.mock import MagicMock

from wxcli.migration.cucm.extractors.moh import (
    MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS,
    MOHExtractor,
)


def _mock_connection(summaries=None, detail=None):
    conn = MagicMock()
    conn.version = "14.0"
    conn.paginated_list = MagicMock(return_value=summaries or [])
    conn.get_detail = MagicMock(return_value=detail)
    return conn


class TestMOHAudioSourceSignature:
    def test_returned_tags_match_the_axl_schema(self):
        assert "sourceFileName" not in MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS
        assert "isDefault" not in MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS
        assert "sourceFile" in MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS
        assert "sourceId" in MOH_AUDIO_SOURCE_LIST_RETURNED_TAGS

    def test_get_detail_keys_on_source_id_not_name(self):
        conn = _mock_connection(
            summaries=[{"sourceId": "1", "name": "SampleAudioSource",
                        "sourceFile": "SampleAudioSource.xml"}],
            detail={"sourceId": "1", "name": "SampleAudioSource",
                    "localeAnnouncement": "English United States"},
        )
        ext = MOHExtractor(conn)
        ext.extract()
        conn.get_detail.assert_called_once_with("getMohAudioSource", sourceId="1")

    def test_skips_detail_when_source_id_missing(self):
        conn = _mock_connection(summaries=[{"name": "Orphan"}])
        ext = MOHExtractor(conn)
        result = ext.extract()
        conn.get_detail.assert_not_called()
        assert result.total == 1
        assert ext.results["moh_sources"][0]["name"] == "Orphan"


class TestMOHFieldAliasing:
    """normalize_moh_source() reads sourceFileName — the alias must supply it."""

    def test_source_file_aliased_for_the_normalizer(self):
        conn = _mock_connection(
            summaries=[{"sourceId": "1", "name": "SampleAudioSource",
                        "sourceFile": "SampleAudioSource.xml"}],
            detail=None,
        )
        ext = MOHExtractor(conn)
        ext.extract()
        src = ext.results["moh_sources"][0]
        assert src["sourceFileName"] == "SampleAudioSource.xml"
        assert src["sourceFile"] == "SampleAudioSource.xml"

    def test_normalizer_receives_the_real_filename(self):
        from wxcli.migration.transform.normalizers import normalize_moh_source

        conn = _mock_connection(
            summaries=[{"sourceId": "1", "name": "SampleAudioSource",
                        "sourceFile": "SampleAudioSource.xml"}],
            detail={"sourceId": "1", "name": "SampleAudioSource",
                    "sourceFile": "SampleAudioSource.xml"},
        )
        ext = MOHExtractor(conn)
        ext.extract()
        obj = normalize_moh_source(ext.results["moh_sources"][0], cluster="lab")
        assert obj.canonical_id == "moh_source:SampleAudioSource"
        assert obj.pre_migration_state["source_file_name"] == "SampleAudioSource.xml"
