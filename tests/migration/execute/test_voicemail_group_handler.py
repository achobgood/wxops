"""Tests for handle_voicemail_group_create execution handler."""

from __future__ import annotations

from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_voicemail_group_create,
)


class TestHandleVoicemailGroupCreate:
    def test_registered_in_handler_registry(self):
        assert ("voicemail_group", "create") in HANDLER_REGISTRY
        assert HANDLER_REGISTRY[("voicemail_group", "create")] is (
            handle_voicemail_group_create
        )

    def test_basic_create_body(self):
        data = {
            "canonical_id": "voicemail_group:Sales Voicemail",
            "name": "Sales Voicemail",
            "extension": "5896",
            "location_id": "location:HQ",
            "language_code": "en_us",
            "passcode": "293847",
            "notifications": {"enabled": True, "destination": "sales@example.com"},
            "message_storage": {"storageType": "INTERNAL"},
            "fax_message": {"enabled": False},
            "transfer_to_number": {"enabled": False},
            "email_copy_of_message": {"enabled": False},
        }
        deps = {"location:HQ": "Y2lzY286LzEzMi8x"}
        ctx = {"orgId": "Y2lzY286Lzk5OQ"}

        calls = handle_voicemail_group_create(data, deps, ctx)

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert (
            "/telephony/config/locations/Y2lzY286LzEzMi8x/voicemailGroups" in url
        )
        assert "orgId=Y2lzY286Lzk5OQ" in url
        assert body["name"] == "Sales Voicemail"
        assert body["extension"] == "5896"
        assert body["passcode"] == "293847"
        assert body["languageCode"] == "en_us"
        assert body["messageStorage"] == {"storageType": "INTERNAL"}
        assert body["notifications"] == {
            "enabled": True,
            "destination": "sales@example.com",
        }
        assert body["faxMessage"] == {"enabled": False}
        assert body["transferToNumber"] == {"enabled": False}
        assert body["emailCopyOfMessage"] == {"enabled": False}

    def test_missing_location_returns_skipped(self):
        """Wave 2A: missing location webex_id is a hard prerequisite miss."""
        from wxcli.migration.execute.handlers import SkippedResult

        data = {
            "canonical_id": "voicemail_group:Orphan",
            "name": "Orphan",
            "extension": "5999",
            "location_id": None,
        }
        deps = {}
        ctx = {"orgId": "Y2lzY286Lzk5OQ"}

        result = handle_voicemail_group_create(data, deps, ctx)
        assert isinstance(result, SkippedResult)
        assert "Orphan" in result.reason

    def test_missing_extension_returns_empty(self):
        data = {
            "canonical_id": "voicemail_group:NoExt",
            "name": "NoExt",
            "extension": None,
            "location_id": "location:HQ",
            "passcode": "293847",
        }
        deps = {"location:HQ": "Y2lzY286LzEzMi8x"}
        ctx = {"orgId": "Y2lzY286Lzk5OQ"}

        assert handle_voicemail_group_create(data, deps, ctx) == []

    def test_resolve_location_from_deps_fallback(self):
        """Verify the _resolve_location_from_deps fallback path.

        When data has no location_id key at all, but deps contains a single
        location entry keyed with the 'location:' prefix, _resolve_location
        returns None and _resolve_location_from_deps picks up the wid.
        """
        data = {
            "canonical_id": "voicemail_group:FallbackVM",
            "name": "FallbackVM",
            "extension": "5100",
            "passcode": "293847",
            # No 'location_id' key at all — forces fallback path
        }
        deps = {"location:HQ": "Y2lzY286LzEzMi8x"}
        ctx = {"orgId": "Y2lzY286Lzk5OQ"}

        calls = handle_voicemail_group_create(data, deps, ctx)

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert "/telephony/config/locations/Y2lzY286LzEzMi8x/voicemailGroups" in url
        assert body["name"] == "FallbackVM"

    def test_caller_id_name_sets_direct_line_and_dial_by_name(self):
        data = {
            "canonical_id": "voicemail_group:Sales Voicemail",
            "name": "Sales Voicemail",
            "extension": "5896",
            "location_id": "location:HQ",
            "caller_id_name": "Sales Team",
            "passcode": "293847",
        }
        deps = {"location:HQ": "loc-wid"}
        ctx = {"orgId": "org-wid"}

        calls = handle_voicemail_group_create(data, deps, ctx)
        body = calls[0][2]
        assert body["directLineCallerIdName"] == {
            "selection": "CUSTOM_NAME",
            "customName": "Sales Team",
        }
        assert body["dialByName"] == "Sales Team"

    def test_phone_number_included_when_present(self):
        data = {
            "canonical_id": "voicemail_group:Sales Voicemail",
            "name": "Sales Voicemail",
            "extension": "5896",
            "location_id": "location:HQ",
            "phone_number": "+16065551234",
            "passcode": "293847",
        }
        deps = {"location:HQ": "loc-wid"}
        ctx = {"orgId": "org-wid"}

        calls = handle_voicemail_group_create(data, deps, ctx)
        body = calls[0][2]
        assert body["phoneNumber"] == "+16065551234"
