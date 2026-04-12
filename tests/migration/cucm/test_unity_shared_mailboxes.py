"""Tests for UnityConnectionClient.extract_shared_mailboxes and
VoicemailExtractor.extract_shared_mailboxes wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from wxcli.migration.cucm.extractors.voicemail import VoicemailExtractor
from wxcli.migration.cucm.unity_connection import UnityConnectionClient


class TestUnityClientExtractSharedMailboxes:
    def test_parses_callhandlers_list(self):
        client = UnityConnectionClient.__new__(UnityConnectionClient)
        client.base_url = "https://uc.example/vmrest"
        client.session = MagicMock()
        client.session.timeout = 30

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Callhandler": [
                {
                    "DisplayName": "Sales Voicemail",
                    "DtmfAccessId": "5896",
                    "ObjectId": "uc-sales",
                    "IsPrimary": "false",
                },
                {
                    "DisplayName": "Primary Mailbox",
                    "DtmfAccessId": "1000",
                    "ObjectId": "uc-primary",
                    "IsPrimary": "true",  # Per-user primary — filtered out
                },
            ]
        }
        client.session.get.return_value = mock_response

        mailboxes = client.extract_shared_mailboxes()

        assert len(mailboxes) == 1
        assert mailboxes[0]["DisplayName"] == "Sales Voicemail"
        assert mailboxes[0]["ObjectId"] == "uc-sales"

    def test_empty_when_request_fails(self):
        client = UnityConnectionClient.__new__(UnityConnectionClient)
        client.base_url = "https://uc.example/vmrest"
        client.session = MagicMock()
        client.session.timeout = 30

        client.session.get.side_effect = Exception("connection refused")

        mailboxes = client.extract_shared_mailboxes()
        assert mailboxes == []

    def test_empty_when_response_non_200(self):
        client = UnityConnectionClient.__new__(UnityConnectionClient)
        client.base_url = "https://uc.example/vmrest"
        client.session = MagicMock()
        client.session.timeout = 30

        mock_response = MagicMock()
        mock_response.status_code = 401
        client.session.get.return_value = mock_response

        mailboxes = client.extract_shared_mailboxes()
        assert mailboxes == []

    def test_handles_single_dict_response_shape(self):
        """CUPI returns a bare dict (not a list) when exactly one handler exists."""
        client = UnityConnectionClient.__new__(UnityConnectionClient)
        client.base_url = "https://uc.example/vmrest"
        client.session = MagicMock()
        client.session.timeout = 30

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Callhandler": {
                "DisplayName": "Solo",
                "DtmfAccessId": "4444",
                "ObjectId": "uc-solo",
                "IsPrimary": "false",
            }
        }
        client.session.get.return_value = mock_response

        mailboxes = client.extract_shared_mailboxes()
        assert len(mailboxes) == 1
        assert mailboxes[0]["DisplayName"] == "Solo"


class TestVoicemailExtractorSharedMailboxes:
    def test_extractor_delegates_to_client(self):
        mock_conn = MagicMock()
        mock_client = MagicMock()
        mock_client.extract_shared_mailboxes.return_value = [
            {"DisplayName": "Sales", "ObjectId": "uc-sales"},
        ]
        extractor = VoicemailExtractor(mock_conn, unity_client=mock_client)

        # extract() should call extract_shared_mailboxes via the client
        # and store the result under results["shared_mailboxes"].
        # AXL methods on mock_conn are mocked away so extract() runs cleanly.
        with patch.object(extractor, "_extract_voicemail_profiles", return_value=[]), \
             patch.object(extractor, "_extract_voicemail_pilots", return_value=[]):
            extractor.extract()

        assert "shared_mailboxes" in extractor.results
        assert extractor.results["shared_mailboxes"] == [
            {"DisplayName": "Sales", "ObjectId": "uc-sales"},
        ]
        mock_client.extract_shared_mailboxes.assert_called_once()

    def test_extractor_no_client_skips_shared_mailboxes(self):
        mock_conn = MagicMock()
        extractor = VoicemailExtractor(mock_conn, unity_client=None)

        with patch.object(extractor, "_extract_voicemail_profiles", return_value=[]), \
             patch.object(extractor, "_extract_voicemail_pilots", return_value=[]):
            extractor.extract()

        assert extractor.results.get("shared_mailboxes", []) == []
