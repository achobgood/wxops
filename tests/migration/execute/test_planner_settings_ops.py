# tests/migration/execute/test_planner_settings_ops.py
"""Test that planner produces configure_settings and configure_voicemail ops."""
from datetime import datetime, timezone
from wxcli.migration.models import (
    CanonicalUser, MigrationStatus, Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.execute.planner import expand_to_operations


def _prov():
    return Provenance(
        source_system="cucm", source_id="pk-test", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def test_user_with_call_settings_produces_configure_settings_op():
    store = MigrationStore(":memory:")
    user = CanonicalUser(
        canonical_id="user:jdoe", provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        emails=["jdoe@test.com"],
        call_settings={"doNotDisturb": {"enabled": True}},
    )
    store.upsert_object(user)

    ops = expand_to_operations(store)
    op_types = [(o.resource_type, o.op_type) for o in ops]
    assert ("user", "create") in op_types
    assert ("user", "configure_settings") in op_types


def test_user_with_voicemail_profile_id_produces_configure_voicemail_op():
    store = MigrationStore(":memory:")
    user = CanonicalUser(
        canonical_id="user:jdoe", provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        emails=["jdoe@test.com"],
        voicemail_profile_id="voicemail_profile:abc123",
    )
    store.upsert_object(user)

    ops = expand_to_operations(store)
    op_types = [(o.resource_type, o.op_type) for o in ops]
    assert ("user", "create") in op_types
    assert ("user", "configure_voicemail") in op_types


def test_user_without_settings_produces_only_create():
    store = MigrationStore(":memory:")
    user = CanonicalUser(
        canonical_id="user:plain", provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        emails=["plain@test.com"],
    )
    store.upsert_object(user)

    ops = expand_to_operations(store)
    op_types = [(o.resource_type, o.op_type) for o in ops]
    assert ("user", "create") in op_types
    assert ("user", "configure_settings") not in op_types
    assert ("user", "configure_voicemail") not in op_types



def test_user_with_both_settings_produces_three_ops():
    """User with both call_settings and voicemail_profile_id gets 3 ops."""
    store = MigrationStore(":memory:")
    user = CanonicalUser(
        canonical_id="user:full", provenance=_prov(),
        status=MigrationStatus.ANALYZED,
        emails=["full@test.com"],
        call_settings={"doNotDisturb": {"enabled": True}},
        voicemail_profile_id="voicemail_profile:xyz",
    )
    store.upsert_object(user)

    ops = expand_to_operations(store)
    op_types = [(o.resource_type, o.op_type) for o in ops]
    assert ("user", "create") in op_types
    assert ("user", "configure_settings") in op_types
    assert ("user", "configure_voicemail") in op_types
    # Only user ops
    user_ops = [o for o in ops if o.resource_type == "user"]
    assert len(user_ops) == 3
