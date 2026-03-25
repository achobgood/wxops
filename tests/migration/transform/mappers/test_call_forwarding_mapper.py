"""Tests for CallForwardingMapper — CUCM per-line forwarding → Webex per-person."""

from __future__ import annotations
from datetime import datetime, timezone
import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.call_forwarding_mapper import (
    CallForwardingMapper,
    _duration_to_rings,
    _is_forwarding_active,
)


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_phone(
    name: str = "SEP001122334455",
    owner_user: str | None = "jdoe",
    lines: list | None = None,
) -> MigrationObject:
    if lines is None:
        lines = [{
            "index": "1",
            "dirn": {"pattern": "1001"},
        }]
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_provenance(source_id=f"uuid-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "owner_user": owner_user,
            "lines": lines,
        },
    )


def _make_user(userid: str = "jdoe") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
    )


def _setup_store_with_phone(phone: MigrationObject, user: MigrationObject | None = None) -> MigrationStore:
    """Create store with a phone and user, plus cross-ref."""
    store = MigrationStore(":memory:")
    store.upsert_object(phone)
    if user:
        store.upsert_object(user)
        store.add_cross_ref(phone.canonical_id, user.canonical_id, "device_owned_by_user")
    return store


class TestDurationToRings:
    def test_30s_is_5_rings(self):
        assert _duration_to_rings(30) == 5

    def test_12s_is_2_rings(self):
        assert _duration_to_rings(12) == 2

    def test_none_returns_none(self):
        assert _duration_to_rings(None) is None

    def test_zero_returns_none(self):
        assert _duration_to_rings(0) is None

    def test_string_input(self):
        assert _duration_to_rings("24") == 4

    def test_clamp_max(self):
        assert _duration_to_rings(999) == 20

    def test_clamp_min(self):
        assert _duration_to_rings(1) == 2


class TestIsForwardingActive:
    def test_with_destination(self):
        assert _is_forwarding_active({"destination": "1234"}) is True

    def test_with_voicemail_true(self):
        assert _is_forwarding_active({"forwardToVoiceMail": "true"}) is True

    def test_empty_dict(self):
        assert _is_forwarding_active({}) is False

    def test_none(self):
        assert _is_forwarding_active(None) is False


class TestCallForwardingMapperCleanForwarding:
    def test_clean_cfa_cfb_cfna_no_decisions(self):
        """Standard CFA/CFB/CFNA with no CUCM-only variants → no decisions."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardAll": {"destination": "+15551234567", "forwardToVoiceMail": "false"},
            "callForwardBusy": {"destination": "", "forwardToVoiceMail": "true"},
            "callForwardNoAnswer": {"destination": "", "forwardToVoiceMail": "true", "duration": "30"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

        # Verify the canonical object was created
        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None

    def test_cfa_destination_stored(self):
        """CFA destination is stored on the canonical object."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardAll": {"destination": "+15551234567", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        mapper.map(store)

        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None
        assert cf_obj.get("always_destination") == "+15551234567"
        assert cf_obj.get("always_enabled") is True

    def test_cfna_duration_converted_to_rings(self):
        """CFNA duration (seconds) is converted to ring count."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardNoAnswer": {"destination": "5559999", "duration": "30"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        mapper.map(store)

        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None
        assert cf_obj.get("no_answer_ring_count") == 5  # 30s / 6 = 5 rings

    def test_cfb_to_voicemail(self):
        """CFB forwardToVoiceMail=true sets busy_to_voicemail=True."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardBusy": {"destination": "", "forwardToVoiceMail": "true"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        mapper.map(store)

        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None
        assert cf_obj.get("busy_to_voicemail") is True
        assert cf_obj.get("busy_enabled") is True

    def test_no_forwarding_no_decisions(self):
        """Phone with no forwarding settings → object created, no decisions."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0


class TestCallForwardingMapperLossy:
    def test_active_busy_int_creates_forwarding_lossy(self):
        """Active callForwardBusyInt → FORWARDING_LOSSY decision."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardBusyInt": {"destination": "5559999", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FORWARDING_LOSSY"

    def test_multiple_lossy_variants_single_decision(self):
        """Multiple active lossy variants → single FORWARDING_LOSSY decision."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardBusyInt": {"destination": "5559999", "forwardToVoiceMail": "false"},
            "callForwardNoAnswerInt": {"destination": "5558888", "forwardToVoiceMail": "false"},
            "callForwardOnFailure": {"destination": "5557777", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FORWARDING_LOSSY"
        assert result.decisions[0].context["lossy_variants"] is not None
        assert len(result.decisions[0].context["lossy_variants"]) == 3

    def test_inactive_lossy_variant_no_decision(self):
        """callForwardBusyInt with empty destination and no VM → no FORWARDING_LOSSY."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardBusyInt": {"destination": "", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 0

    def test_on_failure_active_creates_decision(self):
        """callForwardOnFailure active → FORWARDING_LOSSY decision."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardOnFailure": {"destination": "", "forwardToVoiceMail": "true"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FORWARDING_LOSSY"

    def test_not_registered_active_creates_decision(self):
        """callForwardNotRegistered active → FORWARDING_LOSSY decision."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardNotRegistered": {"destination": "5556666", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        assert len(result.decisions) == 1
        assert result.decisions[0].type.value == "FORWARDING_LOSSY"


class TestCallForwardingMapperMultiLine:
    def test_primary_line_wins(self):
        """Multi-line phone uses primary line (index 1) for forwarding."""
        phone = _make_phone(lines=[
            {
                "index": "2",
                "dirn": {"pattern": "1050"},
                "callForwardAll": {"destination": "WRONG", "forwardToVoiceMail": "false"},
            },
            {
                "index": "1",
                "dirn": {"pattern": "1001"},
                "callForwardAll": {"destination": "+15551234567", "forwardToVoiceMail": "false"},
            },
        ])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None
        assert cf_obj.get("always_destination") == "+15551234567"

    def test_fallback_to_first_line_if_no_index_1(self):
        """If no line with index=1, falls back to first line."""
        phone = _make_phone(lines=[
            {
                "index": "2",
                "dirn": {"pattern": "1050"},
                "callForwardAll": {"destination": "+15551234567", "forwardToVoiceMail": "false"},
            },
        ])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 1
        cf_obj = store.get_object("call_forwarding:jdoe")
        assert cf_obj is not None


class TestCallForwardingMapperNoUser:
    def test_phone_with_no_owner_skipped(self):
        """Phone with no device_owned_by_user cross-ref → skipped."""
        phone = _make_phone()
        store = MigrationStore(":memory:")
        store.upsert_object(phone)
        # No cross-ref added

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0

    def test_phone_with_no_lines_skipped(self):
        """Phone with empty lines list → skipped."""
        phone = MigrationObject(
            canonical_id="phone:SEP001122334455",
            provenance=_provenance(),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"name": "SEP001122334455", "lines": []},
        )
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 0

    def test_empty_store_no_crash(self):
        """Empty store → mapper runs cleanly with zero output."""
        store = MigrationStore(":memory:")

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        assert result.objects_created == 0
        assert len(result.decisions) == 0


class TestCallForwardingMapperMultiDevice:
    def test_second_device_same_user_skipped(self):
        """When user already has call_forwarding object, second phone is skipped."""
        phone1 = _make_phone(name="SEP000000000001")
        phone2 = _make_phone(name="SEP000000000002")
        user = _make_user()

        store = MigrationStore(":memory:")
        store.upsert_object(phone1)
        store.upsert_object(phone2)
        store.upsert_object(user)
        store.add_cross_ref(phone1.canonical_id, user.canonical_id, "device_owned_by_user")
        store.add_cross_ref(phone2.canonical_id, user.canonical_id, "device_owned_by_user")

        mapper = CallForwardingMapper()
        result = mapper.map(store)

        # Only 1 call forwarding object created (first phone wins)
        assert result.objects_created == 1


class TestCallForwardingMapperCrossRef:
    def test_user_has_call_forwarding_cross_ref_created(self):
        """After mapping, user_has_call_forwarding cross-ref is present in store."""
        phone = _make_phone(lines=[{
            "index": "1",
            "dirn": {"pattern": "1001"},
            "callForwardAll": {"destination": "+15551234567", "forwardToVoiceMail": "false"},
        }])
        user = _make_user()
        store = _setup_store_with_phone(phone, user)

        mapper = CallForwardingMapper()
        mapper.map(store)

        refs = store.find_cross_refs("user:jdoe", "user_has_call_forwarding")
        assert len(refs) == 1
        assert refs[0] == "call_forwarding:jdoe"
