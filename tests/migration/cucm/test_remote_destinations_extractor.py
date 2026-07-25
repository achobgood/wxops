"""Tests for RemoteDestinationExtractor — SNR remote destinations."""
from unittest.mock import MagicMock

from wxcli.migration.cucm.extractors.remote_destinations import (
    REMOTE_DEST_LIST_RETURNED_TAGS,
    RemoteDestinationExtractor,
)


def _mock_connection(list_results=None, get_results=None):
    """Build a mock AXLConnection for remote destination extraction."""
    conn = MagicMock()
    conn.version = "14.0"
    list_results = list_results or {}
    get_results = get_results or {}

    def paginated_list(method_name, search_criteria, returned_tags, page_size):
        return list_results.get(method_name, [])

    conn.paginated_list = MagicMock(side_effect=paginated_list)

    def get_detail(method_name, **kwargs):
        return get_results.get(kwargs.get("name"))

    conn.get_detail = MagicMock(side_effect=get_detail)
    return conn


class TestRemoteDestinationAXL14Signature:
    """listRemoteDestination must not request tags absent from the AXL schema."""

    def test_constant_omits_owner_user_id(self):
        assert "ownerUserId" not in REMOTE_DEST_LIST_RETURNED_TAGS
        assert "name" in REMOTE_DEST_LIST_RETURNED_TAGS
        assert "destination" in REMOTE_DEST_LIST_RETURNED_TAGS

    def test_requested_tags_omit_owner_user_id(self):
        conn = _mock_connection()
        ext = RemoteDestinationExtractor(conn)
        ext.extract()

        call = conn.paginated_list.call_args_list[0]
        assert call.args[0] == "listRemoteDestination"
        assert "ownerUserId" not in call.args[2]

    def test_owner_user_id_still_arrives_from_get_detail(self):
        """Owner attribution survives — getRemoteDestination carries ownerUserId."""
        conn = _mock_connection(
            list_results={
                "listRemoteDestination": [
                    {"name": "RD-jdoe", "destination": "+15551234567"},
                ],
            },
            get_results={
                "RD-jdoe": {
                    "name": "RD-jdoe",
                    "destination": "+15551234567",
                    "ownerUserId": "jdoe",
                },
            },
        )
        ext = RemoteDestinationExtractor(conn)
        result = ext.extract()
        dests = ext.results["remote_destinations"]
        assert result.total == 1
        assert result.failed == 0
        assert dests[0]["ownerUserId"] == "jdoe"
