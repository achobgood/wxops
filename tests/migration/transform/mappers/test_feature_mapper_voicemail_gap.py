"""Tests for FeatureMapper voicemail-on-overflow gap detection (Phase A)."""

from __future__ import annotations

from datetime import datetime, timezone

from wxcli.migration.models import (
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper


def _prov(name: str) -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        cluster="lab",
        extracted_at=datetime.now(timezone.utc),
    )


def _hunt_pilot(pattern: str, hunt_list_name: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"hunt_pilot:{pattern}:<None>",
        provenance=_prov(pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "pattern": pattern,
            "hunt_list_name": hunt_list_name,
            "queueCalls": None,
        },
    )


def _hunt_list(name: str, voice_mail_usage: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"hunt_list:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "hunt_list_name": name,
            "voice_mail_usage": voice_mail_usage,
            "line_groups": [],
        },
    )


class TestVoicemailGapDetection:
    def test_use_pilot_number_emits_missing_data(self):
        """Hunt list with voiceMailUsage=USE_PILOT_NUMBER and no matching
        voicemail_group object in the store emits a MISSING_DATA decision."""
        store = MigrationStore(":memory:")
        try:
            store.upsert_object(_hunt_pilot("5000", "SalesHuntList"))
            store.upsert_object(_hunt_list("SalesHuntList", "USE_PILOT_NUMBER"))
            store.add_cross_ref(
                "hunt_pilot:5000:<None>",
                "hunt_list:SalesHuntList",
                "hunt_pilot_has_hunt_list",
            )

            mapper = FeatureMapper()
            result = mapper.map(store)

            voicemail_gaps = [
                d for d in result.decisions
                if d.type == DecisionType.MISSING_DATA
                and d.context.get("reason") == "shared_voicemail_not_extracted"
            ]
            assert len(voicemail_gaps) == 1, (
                f"Expected 1 voicemail gap decision; got {len(voicemail_gaps)}"
            )
            decision = voicemail_gaps[0]
            assert "SalesHuntList" in decision.summary
            assert decision.context["hunt_list_id"] == "hunt_list:SalesHuntList"
            assert decision.context["voice_mail_usage"] == "USE_PILOT_NUMBER"
        finally:
            store.close()

    def test_none_voicemail_usage_no_decision(self):
        """Hunt list with voiceMailUsage=NONE emits no voicemail gap decision."""
        store = MigrationStore(":memory:")
        try:
            store.upsert_object(_hunt_pilot("5001", "NoVmHuntList"))
            store.upsert_object(_hunt_list("NoVmHuntList", "NONE"))
            store.add_cross_ref(
                "hunt_pilot:5001:<None>",
                "hunt_list:NoVmHuntList",
                "hunt_pilot_has_hunt_list",
            )

            mapper = FeatureMapper()
            result = mapper.map(store)

            voicemail_gaps = [
                d for d in result.decisions
                if d.type == DecisionType.MISSING_DATA
                and d.context.get("reason") == "shared_voicemail_not_extracted"
            ]
            assert voicemail_gaps == []
        finally:
            store.close()

    def test_matching_voicemail_group_suppresses_decision(self):
        """If a voicemail_group object is already in the store, no gap decision."""
        store = MigrationStore(":memory:")
        try:
            store.upsert_object(_hunt_pilot("5002", "SupportHuntList"))
            store.upsert_object(_hunt_list("SupportHuntList", "USE_PILOT_NUMBER"))
            store.add_cross_ref(
                "hunt_pilot:5002:<None>",
                "hunt_list:SupportHuntList",
                "hunt_pilot_has_hunt_list",
            )
            store.upsert_object(MigrationObject(
                canonical_id="voicemail_group:Support Voicemail",
                provenance=_prov("Support Voicemail"),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={"name": "Support Voicemail"},
            ))

            mapper = FeatureMapper()
            result = mapper.map(store)

            voicemail_gaps = [
                d for d in result.decisions
                if d.type == DecisionType.MISSING_DATA
                and d.context.get("reason") == "shared_voicemail_not_extracted"
            ]
            assert voicemail_gaps == []
        finally:
            store.close()
