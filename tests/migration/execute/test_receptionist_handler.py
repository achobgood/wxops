"""Tests for receptionist_config handler and planner expansion."""

from __future__ import annotations

from wxcli.migration.execute.handlers import (
    SkippedResult,
    handle_receptionist_config_configure,
)


class TestReceptionistConfigHandler:

    def test_enables_receptionist_client(self):
        """Handler produces PUT /people/{id}/features/reception."""
        data = {
            "canonical_id": "receptionist_config:jdoe@example.com",
            "user_canonical_id": "user:jdoe@example.com",
            "monitored_members": ["user:alice@example.com", "user:bob@example.com"],
            "location_canonical_id": "location:HQ",
        }
        deps = {
            "user:jdoe@example.com": "person-webex-id-123",
            "user:alice@example.com": "person-webex-id-alice",
            "user:bob@example.com": "person-webex-id-bob",
        }
        ctx = {"orgId": "org-123"}

        calls = handle_receptionist_config_configure(data, deps, ctx)

        assert len(calls) >= 1
        method, url, body = calls[0]
        assert method == "PUT"
        assert "/people/person-webex-id-123/features/reception" in url
        assert body["receptionEnabled"] is True
        assert len(body["monitoredMembers"]) == 2

    def test_creates_location_directory(self):
        """Handler produces POST for receptionist contact directory."""
        data = {
            "canonical_id": "receptionist_config:jdoe@example.com",
            "user_canonical_id": "user:jdoe@example.com",
            "monitored_members": ["user:alice@example.com"],
            "location_canonical_id": "location:HQ",
        }
        deps = {
            "user:jdoe@example.com": "person-webex-id-123",
            "user:alice@example.com": "person-webex-id-alice",
            "location:HQ": "loc-webex-id-hq",
        }
        ctx = {"orgId": "org-123"}

        calls = handle_receptionist_config_configure(data, deps, ctx)

        assert len(calls) == 2
        method, url, body = calls[1]
        assert method == "POST"
        assert "/receptionistContacts/directories" in url
        assert body["name"]
        assert len(body["contacts"]) >= 1

    def test_skipped_when_no_person_id(self):
        """Handler returns SkippedResult when user not resolved."""
        data = {
            "canonical_id": "receptionist_config:jdoe@example.com",
            "user_canonical_id": "user:jdoe@example.com",
            "monitored_members": [],
            "location_canonical_id": "location:HQ",
        }
        deps = {}
        ctx = {"orgId": "org-123"}

        result = handle_receptionist_config_configure(data, deps, ctx)
        assert isinstance(result, SkippedResult)
        assert "user:jdoe@example.com" in result.reason

    def test_skips_unresolved_members(self):
        """Unresolved monitored members are silently omitted."""
        data = {
            "canonical_id": "receptionist_config:jdoe@example.com",
            "user_canonical_id": "user:jdoe@example.com",
            "monitored_members": ["user:alice@example.com", "user:gone@example.com"],
            "location_canonical_id": "location:HQ",
        }
        deps = {
            "user:jdoe@example.com": "person-webex-id-123",
            "user:alice@example.com": "person-webex-id-alice",
        }
        ctx = {}

        calls = handle_receptionist_config_configure(data, deps, ctx)
        assert len(calls) >= 1
        _, _, body = calls[0]
        assert len(body["monitoredMembers"]) == 1

    def test_still_enables_even_with_no_members(self):
        """Enable receptionist client even with 0 resolved members."""
        data = {
            "canonical_id": "receptionist_config:jdoe@example.com",
            "user_canonical_id": "user:jdoe@example.com",
            "monitored_members": [],
            "location_canonical_id": "location:HQ",
        }
        deps = {
            "user:jdoe@example.com": "person-webex-id-123",
        }
        ctx = {}

        calls = handle_receptionist_config_configure(data, deps, ctx)
        assert len(calls) >= 1
        _, _, body = calls[0]
        assert body["receptionEnabled"] is True
