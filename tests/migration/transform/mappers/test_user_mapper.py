"""Tests for user_mapper: CUCM End Users -> Webex Calling People.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    LocationAddress,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.user_mapper import UserMapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _provenance(source_id: str = "test-id", name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=source_id,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _cucm_user(
    userid: str = "jsmith",
    mailid: str = "jsmith@acme.com",
    first_name: str = "John",
    last_name: str = "Smith",
    extracted_via_sql: bool = False,
) -> MigrationObject:
    """Create a normalized CUCM user object (base MigrationObject with user type)."""
    state = {}
    if extracted_via_sql:
        state["extracted_via_sql"] = True
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
    )


def _cucm_user_typed(
    userid: str = "jsmith",
    mailid: str = "jsmith@acme.com",
    first_name: str = "John",
    last_name: str = "Smith",
    extracted_via_sql: bool = False,
) -> CanonicalUser:
    """Create a CanonicalUser to store (simulating what normalizer would produce).

    The store identifies the type from the Pydantic class → 'user' via the registry.
    """
    state = {}
    if extracted_via_sql:
        state["extracted_via_sql"] = True
    return CanonicalUser(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state=state,
        cucm_userid=userid,
        cucm_mailid=mailid,
        first_name=first_name,
        last_name=last_name,
    )


def _device(name: str = "SEP001122AABBCC") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device:{name}",
        provenance=_provenance(source_id=f"uuid-dev-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
    )


def _device_pool(name: str = "HQ-Phones") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"device_pool:{name}",
        provenance=_provenance(source_id=f"uuid-dp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
    )


def _location(name: str = "HQ") -> CanonicalLocation:
    return CanonicalLocation(
        canonical_id=f"location:{name}",
        provenance=_provenance(source_id=f"uuid-loc-{name}", name=name),
        status=MigrationStatus.ANALYZED,
        name=name,
        address=LocationAddress(country="US"),
    )


def _dn(pattern: str = "1001", partition: str = "Internal-PT") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"dn:{pattern}:{partition}",
        provenance=_provenance(source_id=f"uuid-dn-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
    )


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_user_with_device_chain(
    store: MigrationStore,
    userid: str = "jsmith",
    mailid: str = "jsmith@acme.com",
    first_name: str = "John",
    last_name: str = "Smith",
    dn_pattern: str = "1001",
    dn_partition: str = "Internal-PT",
    device_name: str = "SEP001122AABBCC",
    dp_name: str = "HQ-Phones",
    loc_name: str = "HQ",
    extracted_via_sql: bool = False,
) -> CanonicalUser:
    """Seed the store with a complete user -> device -> pool -> location chain."""
    user = _cucm_user_typed(
        userid=userid,
        mailid=mailid,
        first_name=first_name,
        last_name=last_name,
        extracted_via_sql=extracted_via_sql,
    )
    dev = _device(device_name)
    dp = _device_pool(dp_name)
    loc = _location(loc_name)
    dn = _dn(dn_pattern, dn_partition)

    store.upsert_object(user)
    store.upsert_object(dev)
    store.upsert_object(dp)
    store.upsert_object(loc)
    store.upsert_object(dn)

    # Cross-refs: user -> device -> pool -> location, user -> primary DN
    store.add_cross_ref(user.canonical_id, dev.canonical_id, "user_has_device")
    store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
    store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
    store.add_cross_ref(user.canonical_id, dn.canonical_id, "user_has_primary_dn")

    return user


# ---------------------------------------------------------------------------
# Tests — happy path
# ---------------------------------------------------------------------------


class TestUserMapperHappyPath:
    """User with email, device, location chain, and primary DN."""

    def test_basic_user_mapping(self):
        store = _make_store()
        _seed_user_with_device_chain(store)

        mapper = UserMapper(create_method="people_api")
        result = mapper.map(store)

        assert result.objects_updated == 1
        assert result.decisions == []

        users = store.get_objects("user")
        assert len(users) == 1
        u = users[0]
        assert u["emails"] == ["jsmith@acme.com"]
        assert u["first_name"] == "John"
        assert u["last_name"] == "Smith"
        assert u["display_name"] == "John Smith"
        assert u["location_id"] == "location:HQ"
        assert u["extension"] == "1001"
        assert u["create_method"] == "people_api"
        assert u["calling_data"] is True
        assert u["status"] == "analyzed"

    def test_mailid_email_resolution(self):
        store = _make_store()
        _seed_user_with_device_chain(store, mailid="jsmith@acme.com")

        mapper = UserMapper()
        mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["emails"] == ["jsmith@acme.com"]

    def test_userid_fallback_for_email(self):
        """When mailid is empty, userid is used as email if it's email-format."""
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:jdoe",
            provenance=_provenance(source_id="uuid-user-jdoe", name="jdoe"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="jdoe@acme.com",
            cucm_mailid="",
            first_name="Jane",
            last_name="Doe",
        )
        dev = _device("SEP002233AABBCC")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")
        dn = _dn("2002", "Internal-PT")

        store.upsert_object(user)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)
        store.upsert_object(dn)

        store.add_cross_ref(user.canonical_id, dev.canonical_id, "user_has_device")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
        store.add_cross_ref(user.canonical_id, dn.canonical_id, "user_has_primary_dn")

        mapper = UserMapper()
        mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["emails"] == ["jdoe@acme.com"]

    def test_extension_from_primary_dn_cross_ref(self):
        """Extension is extracted from the user_has_primary_dn cross-ref target ID."""
        store = _make_store()
        _seed_user_with_device_chain(store, dn_pattern="5001")

        mapper = UserMapper()
        mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["extension"] == "5001"

    def test_create_method_from_config(self):
        store = _make_store()
        _seed_user_with_device_chain(store)

        mapper = UserMapper(create_method="scim")
        mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["create_method"] == "scim"


# ---------------------------------------------------------------------------
# Tests — edge cases and decisions
# ---------------------------------------------------------------------------


class TestUserMapperEdgeCases:
    """Missing email, no device, SQL-extracted users."""

    def test_no_email_produces_missing_data_decision(self):
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:nomail",
            provenance=_provenance(source_id="uuid-user-nomail", name="nomail"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="nomail",
            cucm_mailid="",
        )
        store.upsert_object(user)

        mapper = UserMapper()
        result = mapper.map(store)

        assert result.objects_updated == 0
        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert d.severity == "HIGH"
        assert "no email" in d.summary.lower()

    def test_no_device_produces_missing_data_decision(self):
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:nodev",
            provenance=_provenance(source_id="uuid-user-nodev", name="nodev"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="nodev@acme.com",
            cucm_mailid="nodev@acme.com",
        )
        store.upsert_object(user)
        # No user_has_device cross-ref

        mapper = UserMapper()
        result = mapper.map(store)

        assert result.objects_updated == 0
        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert "no associated phone" in d.summary.lower()

    def test_sql_extracted_user_produces_missing_data_decision(self):
        """SQL-extracted users get MISSING_DATA decision noting limited extraction."""
        store = _make_store()
        _seed_user_with_device_chain(
            store,
            userid="sqluser",
            mailid="sqluser@acme.com",
            extracted_via_sql=True,
        )

        mapper = UserMapper()
        result = mapper.map(store)

        # User should still be created, but with a decision
        assert result.objects_updated == 1
        assert len(result.decisions) == 1
        d = result.decisions[0]
        assert d.type.value == "MISSING_DATA"
        assert d.severity == "LOW"
        assert "sql" in d.summary.lower()
        assert "sql_extracted" in d.context.get("reason", "")
        assert "cucm_css" in d.context.get("missing_fields", [])

    def test_does_not_produce_duplicate_user_decision(self):
        """user_mapper does NOT produce DUPLICATE_USER decisions (analyzer-owned)."""
        store = _make_store()
        # Create two users with the same email
        _seed_user_with_device_chain(
            store,
            userid="user1",
            mailid="same@acme.com",
            device_name="SEP111111111111",
            dp_name="HQ-Phones",
            loc_name="HQ",
            dn_pattern="1001",
        )
        # Second user with different device chain
        user2 = CanonicalUser(
            canonical_id="user:user2",
            provenance=_provenance(source_id="uuid-user-user2", name="user2"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="user2",
            cucm_mailid="same@acme.com",
            first_name="User",
            last_name="Two",
        )
        dev2 = _device("SEP222222222222")
        store.upsert_object(user2)
        store.upsert_object(dev2)
        store.add_cross_ref(user2.canonical_id, dev2.canonical_id, "user_has_device")
        store.add_cross_ref(dev2.canonical_id, "device_pool:HQ-Phones", "device_in_pool")

        mapper = UserMapper()
        result = mapper.map(store)

        # Should not produce any DUPLICATE_USER decisions
        for d in result.decisions:
            assert d.type.value != "DUPLICATE_USER"

    def test_phoneless_user_skipped_by_default(self):
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:phoneless",
            provenance=_provenance(source_id="uuid-user-phoneless", name="phoneless"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="phoneless@acme.com",
            cucm_mailid="phoneless@acme.com",
        )
        store.upsert_object(user)

        mapper = UserMapper(include_phoneless_users=False)
        result = mapper.map(store)

        # Should produce MISSING_DATA decision and skip the user
        assert result.objects_updated == 0
        assert len(result.decisions) == 1

    def test_phoneless_user_included_when_configured(self):
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:phoneless",
            provenance=_provenance(source_id="uuid-user-phoneless", name="phoneless"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="phoneless@acme.com",
            cucm_mailid="phoneless@acme.com",
        )
        store.upsert_object(user)

        mapper = UserMapper(include_phoneless_users=True)
        result = mapper.map(store)

        # User should be created even without a device/location
        assert result.objects_updated == 1
        users = store.get_objects("user")
        assert users[0]["location_id"] is None

    def test_display_name_built_from_first_last(self):
        store = _make_store()
        _seed_user_with_device_chain(
            store, first_name="Alice", last_name="Wonderland"
        )

        mapper = UserMapper()
        mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["display_name"] == "Alice Wonderland"


# ---------------------------------------------------------------------------
# Tests — device line 1 DN fallback for extension resolution
# ---------------------------------------------------------------------------


def _seed_user_with_device_dn_only(
    store: MigrationStore,
    userid: str = "jdoe",
    mailid: str = "jdoe@acme.com",
    first_name: str = "Jane",
    last_name: str = "Doe",
    dn_pattern: str = "2001",
    dn_partition: str = "Internal-PT",
    device_name: str = "SEP003344AABBCC",
    dp_name: str = "HQ-Phones",
    loc_name: str = "HQ",
) -> None:
    """Seed a user with device chain and device_has_dn (ordinal 0), but NO user_has_primary_dn."""
    user = CanonicalUser(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        cucm_userid=userid,
        cucm_mailid=mailid,
        first_name=first_name,
        last_name=last_name,
    )
    dev = _device(device_name)
    dp = _device_pool(dp_name)
    loc = _location(loc_name)
    dn = _dn(dn_pattern, dn_partition)

    store.upsert_object(user)
    store.upsert_object(dev)
    store.upsert_object(dp)
    store.upsert_object(loc)
    store.upsert_object(dn)

    # Cross-refs: user -> device -> pool -> location
    store.add_cross_ref(user.canonical_id, dev.canonical_id, "user_has_device")
    store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
    store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")

    # device -> DN on line 1 (ordinal 0) — NO user_has_primary_dn
    store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn", ordinal=0)


class TestDeviceDNFallback:
    """Extension fallback from device line 1 DN when primaryExtension is absent."""

    def test_extension_from_device_line1_dn(self):
        """When user has no primaryExtension but device has line 1 DN, extension is populated."""
        store = _make_store()
        _seed_user_with_device_dn_only(store, dn_pattern="2001")

        mapper = UserMapper()
        result = mapper.map(store)

        assert result.objects_updated == 1
        users = store.get_objects("user")
        assert users[0]["extension"] == "2001"

    def test_fallback_disabled_by_config(self):
        """When use_device_dn_as_extension is False, extension stays None."""
        store = _make_store()
        _seed_user_with_device_dn_only(store, dn_pattern="2001")

        mapper = UserMapper(use_device_dn_as_extension=False)
        result = mapper.map(store)

        assert result.objects_updated == 1
        users = store.get_objects("user")
        assert users[0]["extension"] is None

    def test_no_device_dn_extension_stays_none(self):
        """When no device has a DN, extension remains None."""
        store = _make_store()
        # Seed user with device chain but NO device_has_dn cross-ref at all
        user = CanonicalUser(
            canonical_id="user:nodn",
            provenance=_provenance(source_id="uuid-user-nodn", name="nodn"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="nodn",
            cucm_mailid="nodn@acme.com",
            first_name="No",
            last_name="DN",
        )
        dev = _device("SEP999999999999")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")

        store.upsert_object(user)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)

        store.add_cross_ref(user.canonical_id, dev.canonical_id, "user_has_device")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
        # No device_has_dn, no user_has_primary_dn

        mapper = UserMapper()
        result = mapper.map(store)

        assert result.objects_updated == 1
        users = store.get_objects("user")
        assert users[0]["extension"] is None

    def test_skips_non_line1_ordinals(self):
        """Only ordinal 0 (line 1) is used; ordinal 1+ are ignored."""
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:multi",
            provenance=_provenance(source_id="uuid-user-multi", name="multi"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="multi",
            cucm_mailid="multi@acme.com",
            first_name="Multi",
            last_name="Line",
        )
        dev = _device("SEPAABBCC112233")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")
        dn_line2 = _dn("9999", "Internal-PT")

        store.upsert_object(user)
        store.upsert_object(dev)
        store.upsert_object(dp)
        store.upsert_object(loc)
        store.upsert_object(dn_line2)

        store.add_cross_ref(user.canonical_id, dev.canonical_id, "user_has_device")
        store.add_cross_ref(dev.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
        # Only a line 2 DN (ordinal 1) — no ordinal 0
        store.add_cross_ref(dev.canonical_id, dn_line2.canonical_id, "device_has_dn", ordinal=1)

        mapper = UserMapper()
        result = mapper.map(store)

        assert result.objects_updated == 1
        users = store.get_objects("user")
        assert users[0]["extension"] is None

    def test_primary_dn_takes_precedence_over_device_dn(self):
        """When both primary DN and device DN exist, primary DN wins."""
        store = _make_store()
        # Full chain with primary DN
        _seed_user_with_device_chain(
            store,
            userid="both",
            mailid="both@acme.com",
            dn_pattern="1001",
            device_name="SEP444444444444",
        )
        # Also add a device_has_dn with a different pattern
        dn_device = _dn("9999", "Other-PT")
        store.upsert_object(dn_device)
        store.add_cross_ref(
            "device:SEP444444444444", dn_device.canonical_id, "device_has_dn", ordinal=0
        )

        mapper = UserMapper()
        result = mapper.map(store)

        users = store.get_objects("user")
        # Primary DN (1001) should win over device DN (9999)
        assert users[0]["extension"] == "1001"

    def test_multi_device_different_line1_dns_logs_warning(self, caplog):
        """When a user has 2+ devices with DIFFERENT line-1 DNs, the mapper
        should emit a logger.warning that surfaces the ambiguity. Selection
        logic is unchanged — first device's DN still wins."""
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:ambig",
            provenance=_provenance(source_id="uuid-user-ambig", name="ambig"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="ambig",
            cucm_mailid="ambig@acme.com",
            first_name="Ambig",
            last_name="User",
        )
        dev1 = _device("SEPAAAAAAAAAAAA")
        dev2 = _device("SEPBBBBBBBBBBBB")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")
        dn1 = _dn("4001", "Internal-PT")  # device 1 line 1 → 4001
        dn2 = _dn("4002", "Internal-PT")  # device 2 line 1 → 4002 (conflict!)

        store.upsert_object(user)
        store.upsert_object(dev1)
        store.upsert_object(dev2)
        store.upsert_object(dp)
        store.upsert_object(loc)
        store.upsert_object(dn1)
        store.upsert_object(dn2)

        store.add_cross_ref(user.canonical_id, dev1.canonical_id, "user_has_device")
        store.add_cross_ref(user.canonical_id, dev2.canonical_id, "user_has_device")
        store.add_cross_ref(dev1.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dev2.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
        # Each device contributes a DIFFERENT line-1 DN — genuine conflict.
        store.add_cross_ref(dev1.canonical_id, dn1.canonical_id, "device_has_dn", ordinal=0)
        store.add_cross_ref(dev2.canonical_id, dn2.canonical_id, "device_has_dn", ordinal=0)

        mapper = UserMapper()
        with caplog.at_level(
            logging.WARNING,
            logger="wxcli.migration.transform.mappers.user_mapper",
        ):
            mapper.map(store)

        users = store.get_objects("user")
        # Selection logic unchanged: first device's DN wins.
        assert users[0]["extension"] in {"4001", "4002"}

        # A warning was emitted and mentions the user and both candidate DNs.
        warnings = [
            r for r in caplog.records
            if r.levelname == "WARNING"
            and "user:ambig" in r.getMessage()
            and "4001" in r.getMessage()
            and "4002" in r.getMessage()
        ]
        assert warnings, (
            f"Expected a warning mentioning user:ambig and both candidate DNs; "
            f"got: {[r.getMessage() for r in caplog.records]}"
        )

    def test_multi_device_same_line1_dn_no_warning(self, caplog):
        """When a user has 2+ devices with the SAME line-1 DN (shared-line style),
        no warning should be emitted — there's no ambiguity to surface."""
        store = _make_store()
        user = CanonicalUser(
            canonical_id="user:noambig",
            provenance=_provenance(source_id="uuid-user-noambig", name="noambig"),
            status=MigrationStatus.NORMALIZED,
            cucm_userid="noambig",
            cucm_mailid="noambig@acme.com",
            first_name="No",
            last_name="Ambig",
        )
        dev1 = _device("SEPCCCCCCCCCCCC")
        dev2 = _device("SEPDDDDDDDDDDDD")
        dp = _device_pool("HQ-Phones")
        loc = _location("HQ")
        dn = _dn("5001", "Internal-PT")

        store.upsert_object(user)
        store.upsert_object(dev1)
        store.upsert_object(dev2)
        store.upsert_object(dp)
        store.upsert_object(loc)
        store.upsert_object(dn)

        store.add_cross_ref(user.canonical_id, dev1.canonical_id, "user_has_device")
        store.add_cross_ref(user.canonical_id, dev2.canonical_id, "user_has_device")
        store.add_cross_ref(dev1.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dev2.canonical_id, dp.canonical_id, "device_in_pool")
        store.add_cross_ref(dp.canonical_id, loc.canonical_id, "device_pool_to_location")
        # BOTH devices reference the same DN on line 1 — classic shared line.
        store.add_cross_ref(dev1.canonical_id, dn.canonical_id, "device_has_dn", ordinal=0)
        store.add_cross_ref(dev2.canonical_id, dn.canonical_id, "device_has_dn", ordinal=0)

        mapper = UserMapper()
        with caplog.at_level(
            logging.WARNING,
            logger="wxcli.migration.transform.mappers.user_mapper",
        ):
            mapper.map(store)

        users = store.get_objects("user")
        assert users[0]["extension"] == "5001"

        # No multi-device DN warning should be present.
        ambiguity_warnings = [
            r for r in caplog.records
            if r.levelname == "WARNING"
            and "different line-1 DNs" in r.getMessage()
        ]
        assert not ambiguity_warnings, (
            f"Did not expect an ambiguity warning for shared-line setup; "
            f"got: {[r.getMessage() for r in caplog.records]}"
        )
