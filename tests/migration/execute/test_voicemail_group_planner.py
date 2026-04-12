"""Tests for voicemail_group planner expansion."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.execute import API_CALL_ESTIMATES, TIER_ASSIGNMENTS
from wxcli.migration.execute.planner import (
    _EXPANDERS,
    _expand_voicemail_group,
)
from wxcli.migration.models import CanonicalVoicemailGroup, Provenance


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="unity_connection",
        source_id=f"uuid-{name}",
        source_name=name,
        cluster="lab",
        extracted_at=datetime.now(timezone.utc),
    )


class TestExpandVoicemailGroup:
    def test_basic_expansion(self):
        vg = CanonicalVoicemailGroup(
            canonical_id="voicemail_group:Sales Voicemail",
            provenance=_prov("Sales Voicemail"),
            name="Sales Voicemail",
            extension="5896",
            location_id="location:HQ",
            passcode="0000",
        )
        ops = _expand_voicemail_group(vg.model_dump())

        assert len(ops) == 1
        op = ops[0]
        assert op.canonical_id == "voicemail_group:Sales Voicemail"
        assert op.op_type == "create"
        assert op.resource_type == "voicemail_group"
        assert op.tier == 4
        assert op.batch == "location:HQ"

    def test_depends_on_location_enable_calling(self):
        vg = CanonicalVoicemailGroup(
            canonical_id="voicemail_group:Sales",
            provenance=_prov("Sales"),
            name="Sales",
            extension="5896",
            location_id="location:HQ",
        )
        ops = _expand_voicemail_group(vg.model_dump())
        assert "location:HQ:enable_calling" in ops[0].depends_on

    def test_no_location_id_no_dependency(self):
        vg = CanonicalVoicemailGroup(
            canonical_id="voicemail_group:Orphan",
            provenance=_prov("Orphan"),
            name="Orphan",
            extension="5999",
            location_id=None,
        )
        ops = _expand_voicemail_group(vg.model_dump())
        # Still produces an op; the batch partitioner handles unbatched ops
        assert len(ops) == 1
        assert ops[0].batch is None
        assert ops[0].depends_on == []


class TestPlannerRegistry:
    def test_tier_assignment(self):
        assert TIER_ASSIGNMENTS.get(("voicemail_group", "create")) == 4

    def test_api_call_estimate(self):
        assert API_CALL_ESTIMATES.get("voicemail_group:create") == 1

    def test_in_expanders_dispatch(self):
        assert "voicemail_group" in _EXPANDERS
