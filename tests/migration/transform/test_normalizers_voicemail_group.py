"""Tests for normalize_voicemail_group and registry wiring."""

from __future__ import annotations

import pytest

from wxcli.migration.models import MigrationObject, MigrationStatus
from wxcli.migration.transform.normalizers import (
    NORMALIZER_REGISTRY,
    RAW_DATA_MAPPING,
    normalize_voicemail_group,
)


class TestNormalizeVoicemailGroup:
    def test_normalize_full_mailbox(self):
        raw = {
            "DisplayName": "Sales Voicemail",
            "Extension": "5896",
            "DtmfAccessId": "5896",
            "ObjectId": "uc-obj-abc-123",
            "pkid": "uc-obj-abc-123",
            "SmtpAddress": "sales-team@example.com",
            "language_code": "en_us",
        }
        obj = normalize_voicemail_group(raw, cluster="lab")

        assert isinstance(obj, MigrationObject)
        assert obj.canonical_id == "voicemail_group:Sales Voicemail"
        assert obj.status == MigrationStatus.NORMALIZED
        state = obj.pre_migration_state
        assert state["name"] == "Sales Voicemail"
        assert state["extension"] == "5896"
        assert state["cucm_object_id"] == "uc-obj-abc-123"
        assert state["notification_destination"] == "sales-team@example.com"

    def test_normalize_falls_back_to_dtmf_access_id(self):
        raw = {
            "DisplayName": "Support",
            "DtmfAccessId": "6000",
            "ObjectId": "uc-obj-xyz",
            "pkid": "uc-obj-xyz",
        }
        obj = normalize_voicemail_group(raw, cluster="lab")
        assert obj.pre_migration_state["extension"] == "6000"

    def test_normalize_provenance_is_unity_connection(self):
        raw = {
            "DisplayName": "Billing",
            "Extension": "5900",
            "ObjectId": "uc-obj-bill",
            "pkid": "uc-obj-bill",
        }
        obj = normalize_voicemail_group(raw, cluster="prod")
        assert obj.provenance.source_system == "unity_connection"
        assert obj.provenance.cluster == "prod"
        assert obj.provenance.source_id == "uc-obj-bill"
        assert obj.provenance.source_name == "Billing"

    def test_normalize_returns_none_when_no_name(self):
        raw = {"DisplayName": "", "Extension": "5896"}
        obj = normalize_voicemail_group(raw, cluster="lab")
        assert obj is None

    def test_registry_contains_voicemail_group(self):
        assert "voicemail_group" in NORMALIZER_REGISTRY
        assert NORMALIZER_REGISTRY["voicemail_group"] is normalize_voicemail_group

    def test_raw_data_mapping_contains_voicemail_group(self):
        expected = ("voicemail", "shared_mailboxes", "voicemail_group")
        assert expected in RAW_DATA_MAPPING
