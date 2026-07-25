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
from wxcli.migration.transform.mappers.line_mapper import LineMapper


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
    owner: str = "jdoe",
) -> MigrationObject:
    """Build a mock raw phone object matching AXL getPhone format.

    The mapper reads raw phone objects with AXL zeep-serialized fields:
    - lines: flat list of {index, label, dirn: {pattern, routePartitionName}}
    - ownerUserName: zeep ref dict {"_value_1": "userid", "uuid": "..."}
    - phoneTemplateName: zeep ref dict
    - speeddials/busyLampFields: nested dicts
    """
    # Convert line_appearances from test format to raw AXL format
    raw_lines = []
    for la in (line_appearances or []):
        raw_lines.append({
            "index": la.get("line_index", 1),
            "label": la.get("line_label", ""),
            "dirn": {
                "pattern": la.get("dn", ""),
                "routePartitionName": {
                    "_value_1": la.get("partition"),
                    "uuid": None,
                },
            },
        })

    state = {
        "name": name,
        "class": "Phone",
        "model": "Cisco 8845",
        "phoneTemplateName": {"_value_1": template_name, "uuid": None},
        "softkeyTemplateName": {"_value_1": None, "uuid": None},
        "ownerUserName": (
            {"_value_1": None, "uuid": None} if is_common_area
            else {"_value_1": owner, "uuid": f"uuid-{owner}"}
        ),
        "devicePoolName": {"_value_1": "DP-HQ", "uuid": None},
        "lines": raw_lines,
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
    # Ensure a device object exists for cross-ref FK constraints
    phone_name = phone.canonical_id.split(":", 1)[-1]
    if device is None:
        device = _make_device(phone_name)
    store.upsert_object(device)
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
    # device_owned_by_user links device:{name}, not phone:{name}
    phone_name = phone.canonical_id.split(":", 1)[-1]
    device_id = f"device:{phone_name}"
    owner_raw = phone.pre_migration_state.get("ownerUserName")
    owner_user = None
    if isinstance(owner_raw, dict):
        owner_user = owner_raw.get("_value_1")
    elif isinstance(owner_raw, str):
        owner_user = owner_raw
    if owner_user:
        user_cid = f"user:{owner_user}"
        if store.get_object(user_cid) is not None:
            store.add_cross_ref(device_id, user_cid, "device_owned_by_user")
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
    def test_shared_dn_on_a_non_owners_device_is_shared_line(self):
        """The appearance belongs to jdoe but sits on jsmith's phone."""
        phone = _make_phone(owner="jsmith", line_appearances=[
            {"line_index": 1, "dn": "1001", "partition": "PT-Internal"},
        ])
        lkt = _make_lkt(line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}])
        line = _make_line("1001")
        shared = CanonicalSharedLine(
            canonical_id="shared_line:1001:PT-Internal",
            provenance=_prov("shared"),
            dn_canonical_id="line:1001",
            owner_canonical_ids=["user:jdoe", "user:jsmith"],
            device_canonical_ids=["device:SEP001122334455", "device:SEP999999999999"],
        )
        store = _setup(
            phone, lkt, users=[_make_user("jdoe"), _make_user("jsmith")],
            lines=[(line, "user:jdoe")], shared_lines=[shared],
        )
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert obj["line_members"][0]["line_type"] == "SHARED_LINE"
        assert obj["line_members"][0]["primary_owner"] is False

    def test_shared_dn_on_its_own_owners_device_stays_primary(self):
        """A shared DN still has exactly one primary appearance — its owner's.

        Typing every appearance SHARED_LINE leaves the line with no
        primaryOwner, which Webex requires exactly one of.
        (docs/prompts/cross-site-phase-2.md — defect N1)
        """
        phone = _make_phone(owner="jdoe", line_appearances=[
            {"line_index": 1, "dn": "1001", "partition": "PT-Internal"},
        ])
        lkt = _make_lkt(line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}])
        line = _make_line("1001")
        shared = CanonicalSharedLine(
            canonical_id="shared_line:1001:PT-Internal",
            provenance=_prov("shared"),
            dn_canonical_id="line:1001",
            owner_canonical_ids=["user:jdoe", "user:jsmith"],
            device_canonical_ids=["device:SEP001122334455", "device:SEP999999999999"],
        )
        store = _setup(
            phone, lkt, users=[_make_user("jdoe")],
            lines=[(line, "user:jdoe")], shared_lines=[shared],
        )
        DeviceLayoutMapper().map(store)
        obj = store.get_object("device_layout:SEP001122334455")
        assert obj["line_members"][0]["line_type"] == "PRIMARY"
        assert obj["line_members"][0]["primary_owner"] is True


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
            {"blfDest": "1002", "label": "Jane", "index": 2},
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


class TestSharedLineEndToEnd:
    """The full pipeline path — no hand-injected shared_line or cross-refs.

    Guards the three defects fixed together in cross-site Phase 2:
      N2  nothing wrote line_assigned_to_user, so member_canonical_id was
          always None and the device-members PUT was never emitted;
      N1  every appearance of a shared DN was typed SHARED_LINE, leaving the
          line with no primary owner;
      and the claim that shared_line: objects are never created (they are —
      by CrossReferenceBuilder._detect_shared_lines, not SharedLineDetector).
    """

    @staticmethod
    def _boss_assistant_store() -> MigrationStore:
        from wxcli.migration.transform.cross_reference import CrossReferenceBuilder

        boss_las = [{"dn": "2000", "partition": "PT-Internal", "line_index": 1}]
        asst_las = [
            {"dn": "2001", "partition": "PT-Internal", "line_index": 1},
            {"dn": "2000", "partition": "PT-Internal", "line_index": 2},
        ]
        store = MigrationStore(":memory:")
        for uid in ("boss", "asst"):
            store.upsert_object(_make_user(uid))
        for name, owner, las in (
            ("SEPAAAA", "boss", boss_las), ("SEPBBBB", "asst", asst_las),
        ):
            raw_lines = [
                {"index": la["line_index"], "label": "",
                 "dirn": {"pattern": la["dn"],
                          "routePartitionName": {"_value_1": la["partition"], "uuid": None}}}
                for la in las
            ]
            store.upsert_object(MigrationObject(
                canonical_id=f"phone:{name}", provenance=_prov(name),
                status=MigrationStatus.NORMALIZED,
                pre_migration_state={
                    "name": name, "class": "Phone", "model": "Cisco 9841",
                    "phoneTemplateName": {"_value_1": "Standard 9841", "uuid": None},
                    "softkeyTemplateName": {"_value_1": None, "uuid": None},
                    "ownerUserName": {"_value_1": owner, "uuid": f"uuid-{owner}"},
                    "devicePoolName": {"_value_1": "DP-HQ", "uuid": None},
                    "lines": raw_lines,
                },
            ))
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:{name}", provenance=_prov(name),
                status=MigrationStatus.ANALYZED, mac=name[3:], model="Cisco 9841",
                owner_canonical_id=f"user:{owner}", line_appearances=las,
                pre_migration_state={"cucm_owner_user": owner, "cucm_device_pool": "DP-HQ"},
            ))
        store.upsert_object(_make_lkt(
            name="Standard 9841",
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"},
                       {"index": 2, "key_type": "PRIMARY_LINE"}],
        ))
        for name in ("SEPAAAA", "SEPBBBB"):
            store.add_cross_ref(
                f"phone:{name}", "line_key_template:Standard 9841",
                "phone_uses_button_template",
            )
        CrossReferenceBuilder(store).build()
        LineMapper().map(store)
        DeviceLayoutMapper().map(store)
        return store

    def test_pipeline_creates_the_shared_line_object(self):
        store = self._boss_assistant_store()
        shared = store.get_objects("shared_line")
        assert [s["canonical_id"] for s in shared] == ["shared_line:2000:PT-Internal"]

    def test_line_assigned_to_user_is_written(self):
        store = self._boss_assistant_store()
        edges = {
            r["from_id"]: r["to_id"]
            for r in store.get_cross_refs(relationship="line_assigned_to_user")
        }
        assert edges == {
            "line:2000:PT-Internal": "user:boss",
            "line:2001:PT-Internal": "user:asst",
        }

    def test_boss_assistant_pair_yields_one_primary_and_one_shared(self):
        store = self._boss_assistant_store()
        boss = store.get_object("device_layout:SEPAAAA")["line_members"]
        asst = store.get_object("device_layout:SEPBBBB")["line_members"]

        # Every member resolves — this is what makes the members PUT fire at all.
        assert all(m["member_canonical_id"] for m in boss + asst)

        # DN 2000 appears on both phones: primary on its owner's, shared on the other.
        boss_2000 = boss[0]
        asst_2000 = next(m for m in asst if m["port"] == 2)
        assert (boss_2000["line_type"], boss_2000["primary_owner"]) == ("PRIMARY", True)
        assert (asst_2000["line_type"], asst_2000["primary_owner"]) == ("SHARED_LINE", False)
        assert boss_2000["member_canonical_id"] == asst_2000["member_canonical_id"] == "user:boss"

        # The assistant's own unshared line is untouched.
        asst_2001 = next(m for m in asst if m["port"] == 1)
        assert (asst_2001["line_type"], asst_2001["primary_owner"]) == ("PRIMARY", True)

    def test_exactly_one_primary_owner_per_shared_dn(self):
        """Webex requires exactly one primaryOwner per line — assert the count."""
        store = self._boss_assistant_store()
        primaries = [
            m
            for name in ("SEPAAAA", "SEPBBBB")
            for m in store.get_object(f"device_layout:{name}")["line_members"]
            if m["member_canonical_id"] == "user:boss" and m["primary_owner"]
        ]
        assert len(primaries) == 1
