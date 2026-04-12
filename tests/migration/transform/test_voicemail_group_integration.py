"""End-to-end voicemail group pipeline integration test."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.transform.engine import TransformEngine
from wxcli.migration.transform.pipeline import normalize_discovery


# Placeholder passcode used by VoicemailGroupMapper (must match mappers/voicemail_group_mapper.py)
_DEFAULT_PASSCODE = "293847"


@pytest.fixture
def store():
    s = MigrationStore(":memory:")
    yield s
    s.close()


def _prov(name: str, system: str = "cucm") -> Provenance:
    return Provenance(
        source_system=system,
        source_id=f"uuid-{name}",
        source_name=name,
        cluster="lab",
        extracted_at=datetime.now(timezone.utc),
    )


class TestVoicemailGroupEndToEnd:
    def test_full_pipeline_creates_voicemail_group_op(self, store):
        # Seed a canonical location + user to anchor location resolution
        store.upsert_object(CanonicalLocation(
            canonical_id="location:HQ",
            provenance=_prov("HQ"),
            status=MigrationStatus.ANALYZED,
            name="HQ",
        ))
        store.upsert_object(CanonicalUser(
            canonical_id="user:jsmith",
            provenance=_prov("jsmith"),
            status=MigrationStatus.ANALYZED,
            extension="1001",
            location_id="location:HQ",
        ))

        # Feed raw_data with a shared mailbox
        raw_data = {
            "voicemail": {
                "voicemail_profiles": [],
                "voicemail_pilots": [],
                "shared_mailboxes": [
                    {
                        "DisplayName": "Sales Voicemail",
                        "DtmfAccessId": "5896",
                        "ObjectId": "uc-sales",
                        "pkid": "uc-sales",
                        "SmtpAddress": "sales@example.com",
                    },
                ],
            },
        }

        # Normalize
        normalize_discovery(raw_data, store, cluster="lab")

        # Run mappers (this invokes VoicemailGroupMapper)
        engine = TransformEngine()
        engine.run(store)

        # Verify mapper output
        vg = store.get_object("voicemail_group:Sales Voicemail")
        assert vg is not None
        assert vg.get("name") == "Sales Voicemail"
        assert vg.get("extension") == "5896"
        assert vg.get("location_id") == "location:HQ"
        assert vg.get("passcode") == _DEFAULT_PASSCODE
        assert vg.get("notifications") == {
            "enabled": True,
            "destination": "sales@example.com",
        }

        # Plan — voicemail_group:create op should appear at tier 4
        ops = expand_to_operations(store)
        vm_ops = [
            op for op in ops
            if op.resource_type == "voicemail_group"
            and op.op_type == "create"
        ]
        assert len(vm_ops) == 1
        op = vm_ops[0]
        assert op.canonical_id == "voicemail_group:Sales Voicemail"
        assert op.tier == 4
        assert op.batch == "location:HQ"
        assert "location:HQ:enable_calling" in op.depends_on

    def test_missing_data_skip_suppresses_op(self, store):
        """Resolving the MISSING_DATA passcode decision as 'skip'
        does NOT suppress the voicemail group — the planner's generic skip
        only triggers on decisions in _SKIP_DECISION_TYPES, which includes
        MISSING_DATA. So ensure this behaves as expected."""
        store.upsert_object(CanonicalLocation(
            canonical_id="location:HQ",
            provenance=_prov("HQ"),
            status=MigrationStatus.ANALYZED,
            name="HQ",
        ))

        raw_data = {
            "voicemail": {
                "voicemail_profiles": [],
                "voicemail_pilots": [],
                "shared_mailboxes": [
                    {
                        "DisplayName": "Sales Voicemail",
                        "DtmfAccessId": "5896",
                        "ObjectId": "uc-sales",
                        "pkid": "uc-sales",
                    },
                ],
            },
        }
        normalize_discovery(raw_data, store, cluster="lab")
        TransformEngine().run(store)

        # Resolve the passcode MISSING_DATA decision as skip
        all_decisions = store.get_all_decisions()
        passcode_decision = next(
            d for d in all_decisions
            if d.get("type") == "MISSING_DATA"
            and d.get("context", {}).get("reason") == "voicemail_group_passcode"
        )
        store.resolve_decision(
            passcode_decision["decision_id"],
            chosen_option="skip",
        )

        ops = expand_to_operations(store)
        vm_ops = [op for op in ops if op.resource_type == "voicemail_group"]
        # The planner's generic skip applies to MISSING_DATA — resolving
        # the passcode decision as "skip" will suppress the voicemail group.
        # This is the documented behavior; test captures it.
        assert vm_ops == []
