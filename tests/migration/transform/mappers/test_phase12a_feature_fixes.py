"""Tests for Phase 12a fixes in feature_mapper, user_mapper, and normalizers.

Covers:
  Fix 1: DN→user resolution for hunt groups (device chain)
  Fix 2: Pickup group CUCM UUID→user resolution
  Fix 3: Feature location_id populated from agents
  Fix 7: Pickup group dedup (empty name → None)
  Fix 8: Cross-refs written (user_in_location, feature_has_agent)

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalUser,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.feature_mapper import (
    FeatureMapper,
    _resolve_agents_from_dns,
    _resolve_dn_to_owner,
)
from wxcli.migration.transform.mappers.user_mapper import UserMapper
from wxcli.migration.transform.normalizers import normalize_pickup_group


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


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _make_dn(pattern: str, partition: str = "PT-Internal") -> MigrationObject:
    """Create a normalized DN object."""
    return MigrationObject(
        canonical_id=f"dn:{pattern}:{partition}",
        provenance=_provenance(source_id=f"uuid-dn-{pattern}", name=pattern),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"pattern": pattern, "routePartitionName": partition},
    )


def _make_device(name: str) -> MigrationObject:
    """Create a normalized device (phone) object."""
    return MigrationObject(
        canonical_id=f"device:{name}",
        provenance=_provenance(source_id=f"uuid-dev-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name, "model": "Cisco 8845"},
    )


def _make_user(
    userid: str,
    email: str = "",
    location_id: str | None = None,
) -> MigrationObject:
    """Create a normalized user object with the fields UserMapper expects."""
    return MigrationObject(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"userid": userid},
        # These are top-level keys the store serializes into data JSON.
        # The user_mapper reads them from the data dict.
    )


def _make_user_full(
    userid: str,
    email: str,
    location_id: str | None = None,
) -> CanonicalUser:
    """Create a CanonicalUser with email and optional location for store seeding."""
    return CanonicalUser(
        canonical_id=f"user:{userid}",
        provenance=_provenance(source_id=f"uuid-user-{userid}", name=userid),
        status=MigrationStatus.NORMALIZED,
        emails=[email],
        cucm_userid=userid,
        location_id=location_id,
    )


def _make_hunt_pilot(
    name: str,
    pattern: str,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"hunt_pilot:{name}",
        provenance=_provenance(source_id=f"uuid-hp-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "pattern": pattern,
            "extension": pattern,
            "enabled": True,
        },
    )


def _make_hunt_list(name: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"hunt_list:{name}",
        provenance=_provenance(source_id=f"uuid-hl-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name, "voiceMailUsage": "NONE"},
    )


def _make_line_group(name: str, algorithm: str = "Top Down") -> MigrationObject:
    return MigrationObject(
        canonical_id=f"line_group:{name}",
        provenance=_provenance(source_id=f"uuid-lg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={"name": name, "distributionAlgorithm": algorithm},
    )


def _make_pickup_group(
    name: str,
    members: list[str] | None = None,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"pickup_group:{name}",
        provenance=_provenance(source_id=f"uuid-pg-{name}", name=name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "members": members or [],
        },
    )


def _seed_hunt_chain_with_device_resolution(
    store: MigrationStore,
    hp_name: str,
    dn_patterns: list[str],
    user_ids: list[str],
) -> str:
    """Seed a full hunt chain with DN→device→user cross-refs.

    Each dn_patterns[i] is assigned to a device, which is owned by user_ids[i].
    Returns the hunt pilot canonical_id.
    """
    hp = _make_hunt_pilot(hp_name, "5001")
    store.upsert_object(hp)

    hl = _make_hunt_list(f"HL-{hp_name}")
    store.upsert_object(hl)
    store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

    lg = _make_line_group(f"LG-{hp_name}")
    store.upsert_object(lg)
    store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")

    for i, pattern in enumerate(dn_patterns):
        dn = _make_dn(pattern)
        store.upsert_object(dn)
        store.add_cross_ref(lg.canonical_id, dn.canonical_id, "line_group_has_members")

        # Device that has this DN
        dev = _make_device(f"SEP00000000{i:04d}")
        store.upsert_object(dev)
        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")

        # User who owns this device
        uid = user_ids[i]
        user = _make_user_full(uid, f"{uid}@example.com", location_id="location:HQ")
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, f"user:{uid}", "device_owned_by_user")

    return hp.canonical_id


# ===========================================================================
# Fix 1: DN→user resolution for hunt groups
# ===========================================================================


class TestFix1DNUserResolutionHuntGroups:
    """Fix 1: DN agents in hunt groups resolve to canonical user IDs
    via the device chain: DN ← device_has_dn ← device → device_owned_by_user → user.
    """

    def test_dn_resolves_to_user_via_device_chain(self):
        """Happy path: DN→device→user resolution produces user canonical_ids in agents."""
        store = _make_store()
        _seed_hunt_chain_with_device_resolution(
            store,
            hp_name="HP-Sales",
            dn_patterns=["1001", "1002"],
            user_ids=["alice", "bob"],
        )

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        agents = hgs[0]["agents"]
        assert "user:alice" in agents
        assert "user:bob" in agents
        # DNs should NOT appear as raw dn: references
        assert not any(a.startswith("dn:") for a in agents)

    def test_dn_with_no_owner_falls_back_to_raw_dn_id(self):
        """DN with no device→user chain falls back to the raw DN canonical_id."""
        store = _make_store()

        hp = _make_hunt_pilot("HP-Orphan", "5010")
        store.upsert_object(hp)

        hl = _make_hunt_list("HL-HP-Orphan")
        store.upsert_object(hl)
        store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

        lg = _make_line_group("LG-HP-Orphan")
        store.upsert_object(lg)
        store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")

        # DN with NO device pointing to it — no device_has_dn cross-ref
        dn = _make_dn("9999")
        store.upsert_object(dn)
        store.add_cross_ref(lg.canonical_id, dn.canonical_id, "line_group_has_members")

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        # Should fall back to raw DN ID
        assert "dn:9999:PT-Internal" in hgs[0]["agents"]

    def test_two_dns_on_same_user_deduplicates_to_one_agent(self):
        """Two DNs owned by the same user should produce only 1 agent entry."""
        store = _make_store()

        hp = _make_hunt_pilot("HP-Dedup", "5020")
        store.upsert_object(hp)

        hl = _make_hunt_list("HL-HP-Dedup")
        store.upsert_object(hl)
        store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

        lg = _make_line_group("LG-HP-Dedup")
        store.upsert_object(lg)
        store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")

        # Two DNs, both on the same user's device
        dn1 = _make_dn("2001")
        dn2 = _make_dn("2002")
        store.upsert_object(dn1)
        store.upsert_object(dn2)
        store.add_cross_ref(lg.canonical_id, dn1.canonical_id, "line_group_has_members")
        store.add_cross_ref(lg.canonical_id, dn2.canonical_id, "line_group_has_members")

        # One device has both DNs
        dev = _make_device("SEP111111110000")
        store.upsert_object(dev)
        store.add_cross_ref(dev.canonical_id, dn1.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dn2.canonical_id, "device_has_dn")

        # One user owns the device
        user = _make_user_full("charlie", "charlie@example.com")
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, "user:charlie", "device_owned_by_user")

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        agents = hgs[0]["agents"]
        # Deduplicated: charlie appears only once
        assert agents.count("user:charlie") == 1
        assert len(agents) == 1


# ===========================================================================
# Fix 2: Pickup group CUCM UUID→user resolution
# ===========================================================================


class TestFix2PickupGroupUUIDResolution:
    """Fix 2: Pickup group members resolve via device chain.
    Members already prefixed with "user:" pass through directly.
    """

    def test_user_prefixed_members_pass_through(self):
        """Members starting with 'user:' are kept as-is."""
        store = _make_store()
        pg = _make_pickup_group("PG-Direct", members=["user:alice", "user:bob"])
        store.upsert_object(pg)

        mapper = FeatureMapper()
        mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped) == 1
        assert "user:alice" in mapped[0]["agents"]
        assert "user:bob" in mapped[0]["agents"]

    def test_dn_based_members_resolve_via_device_chain(self):
        """Members that are DN canonical_ids resolve to user via device chain."""
        store = _make_store()

        # Seed DN→device→user chain
        dn = _make_dn("3001")
        store.upsert_object(dn)

        dev = _make_device("SEP222222220000")
        store.upsert_object(dev)
        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")

        user = _make_user_full("dana", "dana@example.com")
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, "user:dana", "device_owned_by_user")

        # Pickup group with DN reference as member
        pg = _make_pickup_group("PG-DN-Resolve", members=["dn:3001:PT-Internal"])
        store.upsert_object(pg)

        mapper = FeatureMapper()
        mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped) == 1
        assert "user:dana" in mapped[0]["agents"]
        # Raw DN should not appear
        assert "dn:3001:PT-Internal" not in mapped[0]["agents"]

    def test_cucm_uuid_resolves_via_raw_phone_lines(self):
        """CUCM line-level UUIDs resolve to users via raw phone line data."""
        store = _make_store()
        cucm_uuid = "{5782CE0C-0915-1718-87C7-AF59E74F0001}"

        # Store a raw phone object with line UUID → DN mapping
        raw_phone = MigrationObject(
            canonical_id="phone:SEP333333330000",
            provenance=_provenance(source_id="uuid-phone-333", name="SEP333333330000"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={
                "name": "SEP333333330000",
                "lines": {
                    "line": [
                        {
                            "index": 1,
                            "dirn": {
                                "pattern": "4001",
                                "routePartitionName": {
                                    "_value_1": "PT-Internal",
                                    "uuid": "{PT-UUID}",
                                },
                                "uuid": cucm_uuid,
                            },
                        }
                    ]
                },
            },
        )
        store.upsert_object(raw_phone)

        # Seed DN→device→user chain so the DN can resolve to a user
        dn = _make_dn("4001")
        store.upsert_object(dn)
        dev = _make_device("SEP333333330000")
        store.upsert_object(dev)
        store.add_cross_ref(dev.canonical_id, "dn:4001:PT-Internal", "device_has_dn")
        user = _make_user_full("frank", "frank@example.com")
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, "user:frank", "device_owned_by_user")

        # Pickup group with CUCM UUID as member
        pg = _make_pickup_group("PG-UUID-Resolve", members=[cucm_uuid])
        store.upsert_object(pg)

        mapper = FeatureMapper()
        mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped) == 1
        assert "user:frank" in mapped[0]["agents"]
        # Raw CUCM UUID should not appear
        assert cucm_uuid not in mapped[0]["agents"]


# ===========================================================================
# Fix 3: Feature location_id populated from agents
# ===========================================================================


class TestFix3FeatureLocationFromAgents:
    """Fix 3: Features derive location_id from their resolved agents."""

    def test_all_agents_same_location_sets_location_id(self):
        """Hunt group with all agents in same location → location_id set."""
        store = _make_store()
        _seed_hunt_chain_with_device_resolution(
            store,
            hp_name="HP-Loc",
            dn_patterns=["4001", "4002"],
            user_ids=["eve", "frank"],
        )
        # Both users have location_id="location:HQ" (set by _make_user_full in seed helper)

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["location_id"] == "location:HQ"

    def test_no_agents_location_is_none(self):
        """Feature with no agents → location_id is None (no crash)."""
        store = _make_store()

        hp = _make_hunt_pilot("HP-Empty", "5099")
        store.upsert_object(hp)

        hl = _make_hunt_list("HL-HP-Empty")
        store.upsert_object(hl)
        store.add_cross_ref(hp.canonical_id, hl.canonical_id, "hunt_pilot_has_hunt_list")

        lg = _make_line_group("LG-HP-Empty")
        store.upsert_object(lg)
        store.add_cross_ref(hl.canonical_id, lg.canonical_id, "hunt_list_has_line_group")
        # No members in line group

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        assert hgs[0]["location_id"] is None


# ===========================================================================
# Fix 7: Pickup group dedup (normalize_pickup_group)
# ===========================================================================


class TestFix7PickupGroupDedup:
    """Fix 7: normalize_pickup_group returns None for empty/blank names."""

    def test_empty_name_returns_none(self):
        """Pickup group with empty name returns None (skipped)."""
        result = normalize_pickup_group({"name": "", "pattern": ""})
        assert result is None

    def test_none_name_returns_none(self):
        """Pickup group with None name and no pattern returns None."""
        result = normalize_pickup_group({"name": None, "pattern": None})
        assert result is None

    def test_whitespace_only_name_returns_none(self):
        """Pickup group with whitespace-only name returns None."""
        result = normalize_pickup_group({"name": "   ", "pattern": ""})
        assert result is None

    def test_valid_name_returns_migration_object(self):
        """Pickup group with valid name returns a MigrationObject."""
        result = normalize_pickup_group({"name": "PG-Sales", "pattern": "100"})
        assert result is not None
        assert isinstance(result, MigrationObject)
        assert result.canonical_id == "pickup_group:PG-Sales"
        assert result.status == MigrationStatus.NORMALIZED

    def test_pattern_fallback_when_name_empty(self):
        """When name is empty but pattern has a value, pattern is used."""
        result = normalize_pickup_group({"name": "", "pattern": "PG-Fallback"})
        assert result is not None
        assert result.canonical_id == "pickup_group:PG-Fallback"


# ===========================================================================
# Fix 8: Cross-refs written
# ===========================================================================


class TestFix8CrossRefsWritten:
    """Fix 8: Mappers write cross-refs for dependency graph."""

    def test_user_mapper_writes_user_in_location_cross_ref(self):
        """UserMapper writes user_in_location cross-ref when location is resolved."""
        store = _make_store()
        prov = _provenance(source_id="uuid-user-jsmith", name="jsmith")

        # Seed a user object
        user = CanonicalUser(
            canonical_id="user:jsmith",
            provenance=prov,
            status=MigrationStatus.NORMALIZED,
            emails=["jsmith@example.com"],
            cucm_userid="jsmith",
        )
        store.upsert_object(user)

        # Seed a device with a location chain
        dev = _make_device("SEP333333330000")
        store.upsert_object(dev)
        store.add_cross_ref("user:jsmith", dev.canonical_id, "user_has_device")

        # Device pool and location for the chain
        pool = MigrationObject(
            canonical_id="device_pool:DP-HQ",
            provenance=_provenance(source_id="uuid-dp-hq", name="DP-HQ"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"name": "DP-HQ"},
        )
        store.upsert_object(pool)
        store.add_cross_ref(dev.canonical_id, pool.canonical_id, "device_in_pool")

        loc = MigrationObject(
            canonical_id="location:HQ",
            provenance=_provenance(source_id="uuid-loc-hq", name="HQ"),
            status=MigrationStatus.NORMALIZED,
            pre_migration_state={"name": "HQ"},
        )
        store.upsert_object(loc)
        store.add_cross_ref(pool.canonical_id, loc.canonical_id, "device_pool_to_location")

        mapper = UserMapper()
        mapper.map(store)

        # Verify user_in_location cross-ref was written
        refs = store.find_cross_refs("user:jsmith", "user_in_location")
        assert len(refs) == 1
        assert refs[0] == "location:HQ"

    def test_feature_mapper_writes_feature_has_agent_cross_refs(self):
        """FeatureMapper writes feature_has_agent cross-refs for hunt groups."""
        store = _make_store()
        _seed_hunt_chain_with_device_resolution(
            store,
            hp_name="HP-XRef",
            dn_patterns=["6001", "6002"],
            user_ids=["grace", "hank"],
        )

        mapper = FeatureMapper()
        mapper.map(store)

        hgs = store.get_objects("hunt_group")
        assert len(hgs) == 1
        hg_cid = hgs[0]["canonical_id"]

        # Verify feature_has_agent cross-refs were written
        agent_refs = store.find_cross_refs(hg_cid, "feature_has_agent")
        assert len(agent_refs) == 2
        assert "user:grace" in agent_refs
        assert "user:hank" in agent_refs

    def test_feature_mapper_writes_pickup_group_agent_cross_refs(self):
        """FeatureMapper writes feature_has_agent cross-refs for pickup groups."""
        store = _make_store()
        pg = _make_pickup_group("PG-XRef", members=["user:ivan", "user:jane"])
        store.upsert_object(pg)

        mapper = FeatureMapper()
        mapper.map(store)

        pgs = store.get_objects("pickup_group")
        mapped = [p for p in pgs if p["status"] == "analyzed"]
        assert len(mapped) == 1
        pg_cid = mapped[0]["canonical_id"]

        # Verify feature_has_agent cross-refs
        agent_refs = store.find_cross_refs(pg_cid, "feature_has_agent")
        assert len(agent_refs) == 2
        assert "user:ivan" in agent_refs
        assert "user:jane" in agent_refs


# ===========================================================================
# Unit tests for _resolve_dn_to_owner and _resolve_agents_from_dns
# ===========================================================================


class TestResolveDNToOwner:
    """Unit tests for the module-level _resolve_dn_to_owner helper."""

    def test_resolves_dn_to_user_via_device(self):
        store = _make_store()
        dn = _make_dn("7001")
        dev = _make_device("SEP444444440000")
        user = _make_user_full("kim", "kim@example.com")
        store.upsert_object(dn)
        store.upsert_object(dev)
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, dn.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, "user:kim", "device_owned_by_user")

        result = _resolve_dn_to_owner(store, dn.canonical_id)
        assert result == "user:kim"

    def test_returns_none_when_no_device_ref(self):
        store = _make_store()
        dn = _make_dn("7002")
        store.upsert_object(dn)

        result = _resolve_dn_to_owner(store, dn.canonical_id)
        assert result is None

    def test_resolve_agents_from_dns_deduplicates(self):
        """_resolve_agents_from_dns with two DNs mapping to same user → 1 entry."""
        store = _make_store()

        dn1 = _make_dn("8001")
        dn2 = _make_dn("8002")
        dev = _make_device("SEP555555550000")
        user = _make_user_full("leo", "leo@example.com")
        store.upsert_object(dn1)
        store.upsert_object(dn2)
        store.upsert_object(dev)
        store.upsert_object(user)
        store.add_cross_ref(dev.canonical_id, dn1.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, dn2.canonical_id, "device_has_dn")
        store.add_cross_ref(dev.canonical_id, "user:leo", "device_owned_by_user")

        result = _resolve_agents_from_dns(store, [dn1.canonical_id, dn2.canonical_id])
        assert result == ["user:leo"]
