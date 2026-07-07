"""Tests for ReceptionistMapper — receptionist detection from CUCM phone layout signals."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.receptionist_mapper import ReceptionistMapper


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _phone(
    name: str = "SEP001",
    blf_count: int = 0,
    template_name: str = "Standard 8845",
) -> MigrationObject:
    blf_entries = [
        {"blfDest": f"{2000 + i}", "label": f"User {i}"}
        for i in range(blf_count)
    ]
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "busyLampFields": blf_entries,
            "phoneTemplateName": template_name,
        },
    )


def _user(userid: str = "jdoe", extension: str | None = None) -> MigrationObject:
    state: dict = {}
    if extension:
        state["extension"] = extension
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_prov(userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state if state else None,
    )


def _location(
    loc_id: str = "loc-hq",
    main_number: str | None = None,
) -> MigrationObject:
    state: dict = {}
    if main_number:
        state["main_number"] = main_number
    return MigrationObject(
        canonical_id=f"location:{loc_id}",
        provenance=_prov(loc_id),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state if state else None,
    )


def _device_layout(phone_name: str, kem_key_count: int = 0) -> MigrationObject:
    """Create a device_layout object with resolved_kem_keys in pre_migration_state."""
    kem_keys = [{"index": i, "key_type": "SPEED_DIAL"} for i in range(kem_key_count)]
    return MigrationObject(
        canonical_id=f"device_layout:{phone_name}",
        provenance=_prov(phone_name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"resolved_kem_keys": kem_keys} if kem_key_count else {},
    )


def _monitoring_list(
    user_name: str,
    target_ids: list[str],
) -> MigrationObject:
    """Create a monitoring_list object with monitored_members."""
    members = [{"target_canonical_id": tid, "display_label": tid} for tid in target_ids]
    return MigrationObject(
        canonical_id=f"monitoring_list:{user_name}",
        provenance=_prov(user_name),
        status=MigrationStatus.ANALYZED,
        pre_migration_state={"monitored_members": members},
    )


def _setup(
    objects: list[MigrationObject],
    cross_refs: list[tuple[str, str, str]],
) -> MigrationStore:
    store = MigrationStore(":memory:")
    for obj in objects:
        store.upsert_object(obj)
    for from_id, to_id, rel in cross_refs:
        store.add_cross_ref(from_id, to_id, rel)
    return store


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHighBlfDetection:
    def test_high_blf_20_plus_scores_3(self):
        """25 BLF entries alone → score 3, detected."""
        phone = _phone("SEP001", blf_count=25)
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("receptionist_config:jdoe")
        assert config is not None
        assert config["detection_score"] >= 3
        assert config["blf_count"] == 25


class TestMediumBlfAlone:
    def test_medium_blf_10_plus_scores_2_not_detected(self):
        """12 BLF alone → score 2, NOT detected (below threshold of 3)."""
        phone = _phone("SEP001", blf_count=12)
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert store.get_object("receptionist_config:jdoe") is None


class TestMediumBlfPlusKem:
    def test_medium_blf_plus_kem_scores_4(self):
        """12 BLF + KEM → score 4, detected."""
        phone = _phone("SEP001", blf_count=12)
        user = _user("jdoe")
        layout = _device_layout("SEP001", kem_key_count=36)
        store = _setup(
            objects=[phone, user, layout],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("receptionist_config:jdoe")
        assert config is not None
        assert config["detection_score"] == 4
        assert config["has_kem"] is True
        assert config["kem_key_count"] == 36


class TestTemplateNameKeyword:
    def test_template_name_attendant_scores_2(self):
        """12 BLF + 'Attendant Console 8865' template → score 2+2=4, detected."""
        phone = _phone("SEP001", blf_count=12, template_name="Attendant Console 8865")
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("receptionist_config:jdoe")
        assert config is not None
        assert config["detection_score"] == 4
        assert "Attendant Console 8865" in config["template_name"]

    @pytest.mark.parametrize("keyword", ["reception", "lobby", "operator", "front desk"])
    def test_template_keyword_variants(self, keyword: str):
        """Each keyword variant in template name triggers the +2 signal."""
        phone = _phone("SEP001", blf_count=12, template_name=f"Phone {keyword} Template")
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)
        assert result.objects_created == 1


class TestLowBlfNoDetection:
    def test_low_blf_no_detection(self):
        """5 BLF entries → score 0, NOT detected."""
        phone = _phone("SEP001", blf_count=5)
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 0

    def test_no_blf_no_detection(self):
        """0 BLF entries → score 0, NOT detected."""
        phone = _phone("SEP001", blf_count=0)
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 0


class TestMainNumberHolder:
    def test_main_number_holder_adds_score(self):
        """12 BLF + holds main number → score 2+1=3, detected."""
        phone = _phone("SEP001", blf_count=12)
        user = _user("jdoe", extension="5000")
        loc = _location("loc-hq", main_number="5000")
        store = _setup(
            objects=[phone, user, loc],
            cross_refs=[
                ("phone:SEP001", "user:jdoe", "device_owned_by_user"),
                ("user:jdoe", "location:loc-hq", "user_in_location"),
            ],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("receptionist_config:jdoe")
        assert config is not None
        assert config["detection_score"] == 3
        assert config["is_main_number_holder"] is True


class TestCrossRefsWritten:
    def test_cross_refs_written(self):
        """Verify user_has_receptionist_config cross-ref is created."""
        phone = _phone("SEP001", blf_count=25)
        user = _user("jdoe")
        store = _setup(
            objects=[phone, user],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        refs = store.find_cross_refs("user:jdoe", "user_has_receptionist_config")
        assert refs == ["receptionist_config:jdoe"]


class TestMonitoredMembersPopulated:
    def test_monitored_members_populated(self):
        """BLF targets from monitoring_list are copied into monitored_members."""
        phone = _phone("SEP001", blf_count=25)
        user = _user("jdoe")
        ml = _monitoring_list(
            "jdoe",
            target_ids=["user:alice", "user:bob"],
        )
        store = _setup(
            objects=[phone, user, ml],
            cross_refs=[("phone:SEP001", "user:jdoe", "device_owned_by_user")],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        config = store.get_object("receptionist_config:jdoe")
        assert config is not None
        assert "user:alice" in config["monitored_members"]
        assert "user:bob" in config["monitored_members"]


class TestSkipDuplicateUser:
    def test_skip_duplicate_user(self):
        """Multi-device user → only one CanonicalReceptionistConfig produced."""
        phone1 = _phone("SEP001", blf_count=25)
        phone2 = _phone("SEP002", blf_count=25)
        user = _user("jdoe")
        store = _setup(
            objects=[phone1, phone2, user],
            cross_refs=[
                ("phone:SEP001", "user:jdoe", "device_owned_by_user"),
                ("phone:SEP002", "user:jdoe", "device_owned_by_user"),
            ],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 1


class TestNoOwnerSkipped:
    def test_no_owner_skipped(self):
        """Phone with no owner cross-ref → skipped, no config produced."""
        phone = _phone("SEP001", blf_count=25)
        store = _setup(
            objects=[phone],
            cross_refs=[],
        )
        mapper = ReceptionistMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
