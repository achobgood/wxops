"""Tests for SoftkeyMapper — CUCM softkeys → Webex PSK keywords."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.softkey_mapper import (
    SoftkeyMapper,
    CUCM_SOFTKEY_TO_PSK,
    CUCM_STATE_TO_PSK_STATE,
    _is_psk_capable_model,
)


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_softkey_template(
    name: str = "Standard User",
    call_states: dict | None = None,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"softkey_template:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "description": "",
            "default_template": None,
            "call_states": call_states or {},
        },
    )


def _make_phone(name: str, model: str, softkey_template: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "model": model,
            "cucm_softkey_template": softkey_template,
            "cucm_device_pool": None,
            "cucm_owner_user": None,
        },
    )


def _setup(template, phones=None):
    store = MigrationStore(":memory:")
    store.upsert_object(template)
    for p in (phones or []):
        store.upsert_object(p)
        store.add_cross_ref(p.canonical_id, template.canonical_id, "phone_uses_softkey_template")
    return store


class TestPskMapping9800:
    def test_9800_phone_produces_psk_config(self):
        tmpl = _make_softkey_template(call_states={
            "onHook": ["Redial", "NewCall", "DND", "Pickup"],
            "connected": ["Hold", "EndCall", "Trnsfer", "Confrn", "Park"],
        })
        phone = _make_phone("SEP111111111111", "Cisco 9841", "Standard User")
        store = _setup(tmpl, [phone])
        SoftkeyMapper().map(store)
        # Template-level object is now report-only (is_psk_target=False)
        tmpl_obj = store.get_object("softkey_config:Standard User")
        assert tmpl_obj is not None
        assert tmpl_obj["is_psk_target"] is False
        # Per-device object carries is_psk_target=True
        per_device_obj = store.get_object("softkey_config:device:SEP111111111111")
        assert per_device_obj is not None
        assert per_device_obj["is_psk_target"] is True
        # Verify state key lists have mapped keywords
        states = per_device_obj["state_key_lists"]
        assert "idle" in states or "onHook" in states

    def test_mapped_keywords_are_correct(self):
        tmpl = _make_softkey_template(call_states={
            "connected": ["Trnsfer", "Confrn", "Park", "Hold"],
        })
        phone = _make_phone("SEP111111111111", "Cisco 9861", "Standard User")
        store = _setup(tmpl, [phone])
        SoftkeyMapper().map(store)
        obj = store.get_object("softkey_config:Standard User")
        # All of these have PSK equivalents
        assert obj["unmapped_softkeys"] == []


class TestClassicMppFlagOnly:
    def test_8845_phone_not_psk_target(self):
        tmpl = _make_softkey_template(call_states={
            "connected": ["Trnsfer", "Hold"],
        })
        phone = _make_phone("SEP222222222222", "Cisco 8845", "Standard User")
        store = _setup(tmpl, [phone])
        SoftkeyMapper().map(store)
        obj = store.get_object("softkey_config:Standard User")
        assert obj is not None
        assert obj["is_psk_target"] is False


class TestStateMapping:
    def test_cucm_states_map_to_psk_states(self):
        tmpl = _make_softkey_template(call_states={
            "onHook": ["NewCall"],
            "offHook": ["EndCall"],
            "ringIn": ["Answer"],
            "connected": ["Hold"],
            "onHold": ["Resume"],
        })
        phone = _make_phone("SEP111111111111", "Cisco 9841", "Standard User")
        store = _setup(tmpl, [phone])
        SoftkeyMapper().map(store)
        obj = store.get_object("softkey_config:Standard User")
        states = obj["state_key_lists"]
        # Should have mapped state names
        assert len(states) >= 1


class TestUnmappedEntries:
    def test_idivert_qrt_unmapped(self):
        tmpl = _make_softkey_template(call_states={
            "connected": ["iDivert", "QRT", "Hold"],
        })
        phone = _make_phone("SEP111111111111", "Cisco 9841", "Standard User")
        store = _setup(tmpl, [phone])
        SoftkeyMapper().map(store)
        obj = store.get_object("softkey_config:Standard User")
        unmapped_names = [u["cucm_name"] for u in obj["unmapped_softkeys"]]
        assert "iDivert" in unmapped_names
        assert "QRT" in unmapped_names


class TestUsageCount:
    def test_phones_using_populated(self):
        tmpl = _make_softkey_template(call_states={"onHook": ["NewCall"]})
        phones = [
            _make_phone("SEP111111111111", "Cisco 9841", "Standard User"),
            _make_phone("SEP222222222222", "Cisco 9861", "Standard User"),
        ]
        store = _setup(tmpl, phones)
        SoftkeyMapper().map(store)
        obj = store.get_object("softkey_config:Standard User")
        assert obj["phones_using"] == 2


class TestIsPskCapable:
    def test_9800_models(self):
        assert _is_psk_capable_model("Cisco 9841") is True
        assert _is_psk_capable_model("Cisco 9861") is True
        assert _is_psk_capable_model("Cisco IP Phone 9871") is True

    def test_8875(self):
        assert _is_psk_capable_model("Cisco 8875") is True

    def test_classic_mpp(self):
        assert _is_psk_capable_model("Cisco 8845") is False
        assert _is_psk_capable_model("Cisco 7841") is False

    def test_none(self):
        assert _is_psk_capable_model(None) is False
