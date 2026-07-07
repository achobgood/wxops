"""Tests for SNRMapper — CUCM Remote Destinations → Webex Single Number Reach."""

from __future__ import annotations
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.snr_mapper import (
    SNRMapper,
    CUCM_DEFAULT_ANSWER_TOO_SOON,
    CUCM_DEFAULT_ANSWER_TOO_LATE,
)


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_remote_dest(
    name: str = "rd1",
    owner: str = "jdoe",
    destination: str = "+14155551234",
    is_mobile: str = "true",
    enable_mobile_connect: str = "true",
    answer_too_soon: int | None = None,
    answer_too_late: int | None = None,
) -> MigrationObject:
    state = {
        "name": name,
        "destination": destination,
        "ownerUserId": owner,
        "isMobilePhone": is_mobile,
        "enableMobileConnect": enable_mobile_connect,
        "answerTooSoonTimer": answer_too_soon,
        "answerTooLateTimer": answer_too_late,
    }
    return MigrationObject(
        canonical_id=f"remote_destination:{owner}:{name}",
        provenance=_provenance(source_id=f"uuid-rd-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _make_user(userid: str = "jdoe") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
    )


def _setup_store(user, remote_dests):
    store = MigrationStore(":memory:")
    store.upsert_object(user)
    for rd in remote_dests:
        store.upsert_object(rd)
    return store


class TestSNRMapperBasic:
    def test_single_remote_dest_creates_snr(self):
        user = _make_user()
        rd = _make_remote_dest()
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        snr = store.get_object("single_number_reach:jdoe")
        assert snr is not None

    def test_snr_has_correct_fields(self):
        user = _make_user()
        rd = _make_remote_dest(destination="+14155551234")
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        mapper.map(store)

        snr = store.get_object("single_number_reach:jdoe")
        assert snr["user_canonical_id"] == "user:jdoe"
        assert snr["enabled"] is True
        assert len(snr["numbers"]) == 1
        assert snr["numbers"][0]["phone_number"] == "+14155551234"
        assert snr["numbers"][0]["name"] == "Mobile"

    def test_no_remote_dests_no_snr(self):
        user = _make_user()
        store = _setup_store(user, [])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 0

    def test_remote_dest_without_user_skipped(self):
        rd = _make_remote_dest(owner="nonexistent")
        store = MigrationStore(":memory:")
        store.upsert_object(rd)

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 0


class TestSNRMapperMultipleDestinations:
    def test_multiple_dests_same_user(self):
        user = _make_user()
        rd1 = _make_remote_dest(name="rd1", destination="+14155551111")
        rd2 = _make_remote_dest(name="rd2", destination="+14155552222")
        store = _setup_store(user, [rd1, rd2])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        snr = store.get_object("single_number_reach:jdoe")
        assert len(snr["numbers"]) == 2

    def test_different_users_get_separate_snr(self):
        user1 = _make_user("jdoe")
        user2 = _make_user("jane")
        rd1 = _make_remote_dest(name="rd1", owner="jdoe")
        rd2 = _make_remote_dest(name="rd2", owner="jane")
        store = MigrationStore(":memory:")
        store.upsert_object(user1)
        store.upsert_object(user2)
        store.upsert_object(rd1)
        store.upsert_object(rd2)

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 2


class TestSNRMapperLossyTimers:
    def test_default_timers_no_decision(self):
        user = _make_user()
        rd = _make_remote_dest(
            answer_too_soon=CUCM_DEFAULT_ANSWER_TOO_SOON,
            answer_too_late=CUCM_DEFAULT_ANSWER_TOO_LATE,
        )
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

    def test_custom_too_soon_timer_produces_snr_lossy(self):
        user = _make_user()
        rd = _make_remote_dest(answer_too_soon=3000)
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "SNR_LOSSY"
        assert "3000" in str(d.context["lossy_timers"])

    def test_custom_too_late_timer_produces_snr_lossy(self):
        user = _make_user()
        rd = _make_remote_dest(answer_too_late=25000)
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "SNR_LOSSY"

    def test_null_timers_use_defaults_no_decision(self):
        user = _make_user()
        rd = _make_remote_dest(answer_too_soon=None, answer_too_late=None)
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0


class TestSNRMapperCrossRefs:
    def test_user_has_snr_cross_ref_created(self):
        user = _make_user()
        rd = _make_remote_dest()
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        mapper.map(store)

        refs = store.find_cross_refs("user:jdoe", "user_has_snr")
        assert len(refs) == 1
        assert refs[0] == "single_number_reach:jdoe"


class TestSNRMapperDisabled:
    def test_disabled_mobile_connect(self):
        user = _make_user()
        rd = _make_remote_dest(enable_mobile_connect="false")
        store = _setup_store(user, [rd])

        mapper = SNRMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        snr = store.get_object("single_number_reach:jdoe")
        assert snr["enabled"] is False
        assert snr["numbers"][0]["enabled"] is False
