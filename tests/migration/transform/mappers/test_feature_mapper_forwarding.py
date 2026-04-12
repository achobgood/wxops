"""Tests for FeatureMapper forwarding/overflow/holiday/night extraction.

Verifies that hunt pilot AXL fields (forwardHuntNoAnswer, forwardHuntBusy,
queueCalls.queueFullDestination, etc.) flow into the canonical hunt group /
call queue objects, and that CTI route point forwarding flows into the
canonical auto attendant.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from wxcli.migration.models import (
    CanonicalCallQueue,
    CanonicalHuntGroup,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.feature_mapper import FeatureMapper


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _provenance(source_id: str) -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=source_id,
        extracted_at=datetime.utcnow(),
    )


def _put_hunt_pilot(store: MigrationStore, hp_id: str, state: dict) -> None:
    # canonical_id prefix "hunt_pilot:..." drives object_type detection
    obj = MigrationObject(
        canonical_id=hp_id,
        provenance=_provenance(hp_id.split(":", 1)[-1]),
        status=MigrationStatus.DISCOVERED,
        pre_migration_state=state,
    )
    store.upsert_object(obj)


def _put_cti_rp(store: MigrationStore, rp_id: str, state: dict) -> None:
    # canonical_id prefix "cti_rp:..." drives object_type detection
    obj = MigrationObject(
        canonical_id=rp_id,
        provenance=_provenance(rp_id.split(":", 1)[-1]),
        status=MigrationStatus.DISCOVERED,
        pre_migration_state=state,
    )
    store.upsert_object(obj)


def _get_only_call_queue(store: MigrationStore) -> dict:
    queues = store.get_objects("call_queue")
    assert len(queues) == 1
    return queues[0]


def _get_only_hunt_group(store: MigrationStore) -> dict:
    hgs = store.get_objects("hunt_group")
    assert len(hgs) == 1
    return hgs[0]


def _get_only_auto_attendant(store: MigrationStore) -> dict:
    aas = store.get_objects("auto_attendant")
    assert len(aas) == 1
    return aas[0]


class TestHuntGroupForwardingExtraction:
    def test_forward_no_answer_destination_extracted(self):
        store = _make_store()
        _put_hunt_pilot(store, "hunt_pilot:HP1", {
            "name": "Sales HG",
            "pattern": "5000",
            "extension": "5000",
            "forwardHuntNoAnswer": {"destination": "5999"},
        })
        FeatureMapper().map(store)
        hg = _get_only_hunt_group(store)
        assert hg["forward_no_answer_enabled"] is True
        assert hg["forward_no_answer_destination"] == "5999"

    def test_forward_busy_destination_extracted(self):
        store = _make_store()
        _put_hunt_pilot(store, "hunt_pilot:HP2", {
            "name": "Support HG",
            "extension": "5100",
            "forwardHuntBusy": {"destination": "5199"},
        })
        FeatureMapper().map(store)
        hg = _get_only_hunt_group(store)
        assert hg["forward_busy_enabled"] is True
        assert hg["forward_busy_destination"] == "5199"

    def test_no_forwarding_leaves_defaults(self):
        store = _make_store()
        _put_hunt_pilot(store, "hunt_pilot:HP3", {
            "name": "Plain HG",
            "extension": "5200",
        })
        FeatureMapper().map(store)
        hg = _get_only_hunt_group(store)
        assert hg["forward_always_enabled"] is False
        assert hg["forward_busy_enabled"] is False
        assert hg["forward_no_answer_enabled"] is False
        assert hg["forward_no_answer_destination"] is None


class TestCallQueueOverflowExtraction:
    def test_queue_full_destination_extracted(self):
        store = _make_store()
        _put_hunt_pilot(store, "hunt_pilot:CQ1", {
            "name": "Sales CQ",
            "extension": "6000",
            "queueCalls": {
                "enabled": True,
                "maxCallersInQueue": 25,
                "queueFullDestination": "+15555550100",
                "maxWaitTimeDestination": "+15555550101",
                "maxWaitTime": 120,
                "noAgentDestination": "+15555550102",
            },
        })
        FeatureMapper().map(store)
        cq = _get_only_call_queue(store)
        assert cq["queue_full_destination"] == "+15555550100"
        assert cq["max_wait_time_destination"] == "+15555550101"
        assert cq["max_wait_time"] == 120
        assert cq["no_agent_destination"] == "+15555550102"

    def test_queue_overflow_optional(self):
        store = _make_store()
        _put_hunt_pilot(store, "hunt_pilot:CQ2", {
            "name": "Min CQ",
            "extension": "6100",
            "queueCalls": {"enabled": True, "maxCallersInQueue": 10},
        })
        FeatureMapper().map(store)
        cq = _get_only_call_queue(store)
        assert cq["queue_full_destination"] is None
        assert cq["no_agent_destination"] is None
        assert cq["max_wait_time"] is None


class TestAutoAttendantForwardingExtraction:
    def test_cti_rp_with_forward_destination(self):
        store = _make_store()
        _put_cti_rp(store, "cti_rp:RP1", {
            "name": "Main AA",
            "pattern": "7000",
            "callForwardAll": {"destination": "+15555559999"},
        })
        FeatureMapper().map(store)
        aa = _get_only_auto_attendant(store)
        assert aa["forward_always_enabled"] is True
        assert aa["forward_always_destination"] == "+15555559999"

    def test_cti_rp_without_forward_destination(self):
        store = _make_store()
        _put_cti_rp(store, "cti_rp:RP2", {
            "name": "No Forward AA",
            "pattern": "7100",
        })
        FeatureMapper().map(store)
        aa = _get_only_auto_attendant(store)
        assert aa["forward_always_enabled"] is False
        assert aa["forward_always_destination"] is None
