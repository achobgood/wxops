"""Tests for DeviceLayoutMapper — per-phone resolved layouts."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalLineKeyTemplate,
    CanonicalSharedLine,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.device_layout_mapper import DeviceLayoutMapper


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_phone(
    name: str = "SEP001122334455",
    template_name: str = "Standard 8845",
    line_appearances: list[dict] | None = None,
    speed_dials: list | None = None,
    blf_entries: list | None = None,
    is_common_area: bool = False,
) -> MigrationObject:
    state = {
        "name": name,
        "cucm_phone_template": template_name,
        "cucm_device_pool": None,
        "cucm_owner_user": "jdoe",
        "is_common_area": is_common_area,
        "line_appearances": line_appearances or [],
    }
    if speed_dials is not None:
        state["speeddials"] = {"speeddial": speed_dials}
    if blf_entries is not None:
        state["busyLampFields"] = {"busyLampField": blf_entries}
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_lkt(
    name: str = "Standard 8845",
    line_keys: list[dict] | None = None,
    kem_keys: list[dict] | None = None,
) -> CanonicalLineKeyTemplate:
    return CanonicalLineKeyTemplate(
        canonical_id=f"line_key_template:{name}",
        provenance=_prov(name),
        status=MigrationStatus.ANALYZED,
        name=name,
        line_keys=line_keys or [],
        kem_keys=kem_keys or [],
    )


def _make_user(userid: str = "jdoe") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_prov(userid),
        status=MigrationStatus.NORMALIZED,
    )


def _make_line(pattern: str, owner: str | None = None) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"line:{pattern}",
        provenance=_prov(pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"extension": pattern, "pattern": pattern},
    )


def _make_device(name: str = "SEP001122334455") -> CanonicalDevice:
    return CanonicalDevice(
        canonical_id=f"device:{name}",
        provenance=_prov(name),
        status=MigrationStatus.ANALYZED,
        mac=name[3:] if name.startswith("SEP") else None,
        model="Cisco 8845",
    )


def _setup(phone, lkt, device=None, users=None, lines=None, shared_lines=None):
    store = MigrationStore(":memory:")
    store.upsert_object(phone)
    store.upsert_object(lkt)
    if device:
        store.upsert_object(device)
    for u in (users or []):
        store.upsert_object(u)
    for ln, owner_id in (lines or []):
        store.upsert_object(ln)
        if owner_id:
            store.add_cross_ref(ln.canonical_id, owner_id, "line_assigned_to_user")
    for sl in (shared_lines or []):
        store.upsert_object(sl)
    store.add_cross_ref(
        phone.canonical_id, lkt.canonical_id, "phone_uses_button_template"
    )
    owner_refs = phone.pre_migration_state.get("cucm_owner_user")
    if owner_refs:
        # Only add cross-ref if the user object is in the store (FK constraint)
        user_cid = f"user:{owner_refs}"
        if store.get_object(user_cid) is not None:
            store.add_cross_ref(phone.canonical_id, user_cid, "device_owned_by_user")
    return store


class TestLineResolution:
    def test_line_resolved_to_user(self):
        phone = _make_phone(line_appearances=[
            {"line_index": 1, "dn": "1001", "partition": "PT-Internal"},
        ])
        lkt = _make_lkt(line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}])
        user = _make_user("jdoe")
        line = _make_line("1001")
        store = _setup(phone, lkt, users=[user], lines=[(line, "user:jdoe")])
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert obj is not None
        assert len(obj["line_members"]) == 1
        assert obj["line_members"][0]["member_canonical_id"] == "user:jdoe"
        assert obj["line_members"][0]["line_type"] == "PRIMARY"


class TestSharedLineDetection:
    def test_shared_dn_sets_shared_line_type(self):
        phone = _make_phone(line_appearances=[
            {"line_index": 1, "dn": "1001", "partition": "PT-Internal"},
        ])
        lkt = _make_lkt(line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}])
        user = _make_user("jdoe")
        line = _make_line("1001")
        shared = CanonicalSharedLine(
            canonical_id="shared_line:1001:PT-Internal",
            provenance=_prov("shared"),
            dn_canonical_id="line:1001",
            owner_canonical_ids=["user:jdoe", "user:jsmith"],
            device_canonical_ids=["device:SEP001122334455", "device:SEP999999999999"],
        )
        store = _setup(phone, lkt, users=[user], lines=[(line, "user:jdoe")], shared_lines=[shared])
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert obj["line_members"][0]["line_type"] == "SHARED_LINE"


class TestSpeedDialMerge:
    def test_speed_dial_values_merged(self):
        phone = _make_phone(speed_dials=[
            {"speedDialIndex": "2", "speedDialNumber": "5551234", "label": "Lobby"},
        ])
        lkt = _make_lkt(line_keys=[
            {"index": 1, "key_type": "PRIMARY_LINE"},
            {"index": 2, "key_type": "SPEED_DIAL"},
        ])
        store = _setup(phone, lkt)
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert len(obj["speed_dials"]) == 1
        assert obj["speed_dials"][0]["number"] == "5551234"
        assert obj["speed_dials"][0]["label"] == "Lobby"


class TestBlfTargetResolution:
    def test_blf_target_resolved_to_user(self):
        phone = _make_phone(blf_entries=[
            {"blfDest": "1002", "label": "Jane"},
        ])
        lkt = _make_lkt(line_keys=[
            {"index": 1, "key_type": "PRIMARY_LINE"},
            {"index": 2, "key_type": "MONITOR"},
        ])
        user = _make_user("jdoe")
        target_user = _make_user("jsmith")
        target_line = _make_line("1002")
        store = _setup(phone, lkt, users=[user, target_user],
                       lines=[(target_line, "user:jsmith")])
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        monitor_keys = [k for k in obj["resolved_line_keys"] if k["key_type"] == "MONITOR"]
        assert len(monitor_keys) == 1
        assert monitor_keys[0]["target_canonical_id"] == "user:jsmith"


class TestKemMerge:
    def test_kem_keys_populated(self):
        phone = _make_phone(speed_dials=[
            {"speedDialIndex": "3", "speedDialNumber": "5559999", "label": "KEM SD"},
        ])
        lkt = _make_lkt(
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}, {"index": 2, "key_type": "LINE"}],
            kem_keys=[{"index": 3, "key_type": "SPEED_DIAL"}],
        )
        store = _setup(phone, lkt)
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert len(obj["resolved_kem_keys"]) >= 1


class TestSkipsCommonArea:
    def test_common_area_phones_skipped(self):
        phone = _make_phone(is_common_area=True)
        lkt = _make_lkt(line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}])
        store = _setup(phone, lkt)
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert obj is None


class TestMissingTemplate:
    def test_phone_with_no_template_gets_basic_layout(self):
        phone = _make_phone(
            template_name="NonExistent",
            line_appearances=[{"line_index": 1, "dn": "1001", "partition": None}],
        )
        lkt = _make_lkt(name="NonExistent", line_keys=[])
        # Don't add the template to store — simulate missing
        store = MigrationStore(":memory:")
        store.upsert_object(phone)
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        # Should still create a layout from line_appearances alone
        assert obj is not None
