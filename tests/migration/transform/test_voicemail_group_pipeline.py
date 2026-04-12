"""Integration test: raw_data -> normalize_discovery -> voicemail_group in store."""

from __future__ import annotations

import pytest

from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.pipeline import normalize_discovery


@pytest.fixture
def store():
    s = MigrationStore(":memory:")
    yield s
    s.close()


class TestVoicemailGroupNormalizationPipeline:
    def test_shared_mailbox_normalized_into_store(self, store):
        raw_data = {
            "voicemail": {
                "voicemail_profiles": [],
                "voicemail_pilots": [],
                "shared_mailboxes": [
                    {
                        "DisplayName": "Sales Voicemail",
                        "DtmfAccessId": "5896",
                        "ObjectId": "uc-sales-1",
                        "pkid": "uc-sales-1",
                        "SmtpAddress": "sales-team@example.com",
                    },
                    {
                        "DisplayName": "Support Voicemail",
                        "DtmfAccessId": "5897",
                        "ObjectId": "uc-support-1",
                        "pkid": "uc-support-1",
                    },
                ],
            },
        }

        summary = normalize_discovery(raw_data, store, cluster="lab")

        assert summary["pass1"].get("voicemail/shared_mailboxes") == 2

        sales = store.get_object("voicemail_group:Sales Voicemail")
        support = store.get_object("voicemail_group:Support Voicemail")

        assert sales is not None
        assert sales["pre_migration_state"]["extension"] == "5896"
        assert sales["pre_migration_state"]["notification_destination"] == (
            "sales-team@example.com"
        )
        assert support is not None
        assert support["pre_migration_state"]["extension"] == "5897"

    def test_no_shared_mailboxes_no_error(self, store):
        raw_data = {
            "voicemail": {
                "voicemail_profiles": [],
                "voicemail_pilots": [],
            },
        }

        # Should not raise
        normalize_discovery(raw_data, store, cluster="lab")

        # No voicemail_group objects created
        vms = list(store.get_objects("voicemail_group"))
        assert vms == []
