"""Tests for preflight check functions.

All tests mock wxcli subprocess output — no live Webex calls.
(from phase-10-preflight.md, testing approach)
"""

import pytest
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalLine,
    CanonicalLocation,
    CanonicalTrunk,
    CanonicalUser,
    CanonicalWorkspace,
    CanonicalHuntGroup,
    CanonicalCallQueue,
    CanonicalAutoAttendant,
    CanonicalPagingGroup,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.preflight import CheckStatus
from wxcli.migration.preflight.checks import (
    check_licenses,
    check_workspace_licenses,
    check_locations,
    check_trunks,
    check_feature_entitlements,
    check_number_conflicts,
    check_duplicate_users,
    check_rate_limit_budget,
)
from wxcli.migration.store import MigrationStore


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


def _add_plan_op(store, canonical_id, resource_type="user", op_type="create"):
    """Add a plan_operations row so preflight checks see the object."""
    store.conn.execute(
        "INSERT OR IGNORE INTO plan_operations "
        "(node_id, canonical_id, resource_type, op_type, tier, batch, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (f"{canonical_id}:{op_type}", canonical_id, resource_type, op_type, 2, "site-1", "pending"),
    )
    store.conn.commit()


# ===================================================================
# Check 1: User Licenses
# ===================================================================


class TestCheckLicenses:
    def test_pass_sufficient_licenses(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["a@test.com"],
        )))
        _add_plan_op(store, "user:001")
        licenses = [{"name": "Webex Calling - Professional", "totalUnits": 100, "consumedUnits": 50}]
        result = check_licenses(store, licenses)
        assert result.status == CheckStatus.PASS
        assert "1 needed" in result.detail

    def test_fail_insufficient_licenses(self, store):
        for i in range(10):
            store.upsert_object(_analyzed(CanonicalUser(
                canonical_id=f"user:{i:03d}", provenance=_prov(), emails=[f"u{i}@test.com"],
            )))
            _add_plan_op(store, f"user:{i:03d}")
        licenses = [{"name": "Webex Calling - Professional", "totalUnits": 20, "consumedUnits": 15}]
        result = check_licenses(store, licenses)
        assert result.status == CheckStatus.FAIL
        assert "SHORT" in result.detail

    def test_fail_no_calling_license(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["a@test.com"],
        )))
        _add_plan_op(store, "user:001")
        licenses = [{"name": "Webex Messaging", "totalUnits": 100, "consumedUnits": 0}]
        result = check_licenses(store, licenses)
        assert result.status == CheckStatus.FAIL

    def test_skip_no_users(self, store):
        result = check_licenses(store, [])
        assert result.status == CheckStatus.SKIP

    def test_warn_low_buffer(self, store):
        for i in range(100):
            store.upsert_object(_analyzed(CanonicalUser(
                canonical_id=f"user:{i:03d}", provenance=_prov(), emails=[f"u{i}@test.com"],
            )))
            _add_plan_op(store, f"user:{i:03d}")
        licenses = [{"name": "Webex Calling - Professional", "totalUnits": 105, "consumedUnits": 0}]
        result = check_licenses(store, licenses)
        assert result.status == CheckStatus.WARN
        assert "buffer" in result.detail


# ===================================================================
# Check 2: Workspace Licenses
# ===================================================================


class TestCheckWorkspaceLicenses:
    def test_pass(self, store):
        store.upsert_object(_analyzed(CanonicalWorkspace(
            canonical_id="workspace:001", provenance=_prov(), display_name="Lobby",
        )))
        licenses = [{"name": "Webex Calling - Workspaces", "totalUnits": 50, "consumedUnits": 10}]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.PASS

    def test_fail(self, store):
        for i in range(10):
            store.upsert_object(_analyzed(CanonicalWorkspace(
                canonical_id=f"workspace:{i:03d}", provenance=_prov(), display_name=f"WS-{i}",
            )))
        licenses = [{"name": "Webex Calling - Workspaces", "totalUnits": 5, "consumedUnits": 0}]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.FAIL

    def test_skip_no_workspaces(self, store):
        result = check_workspace_licenses(store, [])
        assert result.status == CheckStatus.SKIP

    def test_warn_low_buffer(self, store):
        for i in range(100):
            store.upsert_object(_analyzed(CanonicalWorkspace(
                canonical_id=f"workspace:{i:03d}", provenance=_prov(), display_name=f"WS-{i}",
            )))
        licenses = [{"name": "Webex Calling - Workspaces", "totalUnits": 105, "consumedUnits": 0}]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.WARN
        assert "buffer" in result.detail


# ===================================================================
# Check 3: Locations
# ===================================================================


class TestCheckLocations:
    def test_pass_all_exist(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="HQ Office",
        )))
        webex_locs = [{"name": "HQ Office", "id": "loc-123"}]
        result = check_locations(store, webex_locs)
        assert result.status == CheckStatus.PASS

    def test_fail_missing_location(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="HQ Office",
        )))
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:branch", provenance=_prov(), name="Seattle Branch",
        )))
        webex_locs = [{"name": "HQ Office", "id": "loc-123"}]
        result = check_locations(store, webex_locs)
        assert result.status == CheckStatus.FAIL
        assert "Seattle Branch" in result.detail

    def test_case_insensitive_match(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="hq office",
        )))
        webex_locs = [{"name": "HQ Office", "id": "loc-123"}]
        result = check_locations(store, webex_locs)
        assert result.status == CheckStatus.PASS

    def test_skip_no_locations(self, store):
        result = check_locations(store, [])
        assert result.status == CheckStatus.SKIP


# ===================================================================
# Check 3b: Locations — PSTN Connection Sub-check
# ===================================================================


class TestCheckLocationsPSTN:
    def test_pass_all_locations_have_pstn(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="HQ Office",
        )))
        webex_locs = [{"name": "HQ Office", "id": "loc-123"}]
        pstn_connections = {"loc-123": {"routingChoice": "TRUNK", "trunkId": "trunk-1"}}
        result = check_locations(store, webex_locs, pstn_connections=pstn_connections)
        assert result.status == CheckStatus.PASS
        assert "all have PSTN" in result.detail

    def test_warn_location_missing_pstn(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="HQ Office",
        )))
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:branch", provenance=_prov(), name="Seattle Branch",
        )))
        webex_locs = [
            {"name": "HQ Office", "id": "loc-123"},
            {"name": "Seattle Branch", "id": "loc-456"},
        ]
        pstn_connections = {"loc-123": {"routingChoice": "TRUNK"}}
        result = check_locations(store, webex_locs, pstn_connections=pstn_connections)
        assert result.status == CheckStatus.WARN
        assert any(i.issue_type == "PSTN_NOT_CONFIGURED" for i in result.issues)
        assert "Seattle Branch" in result.detail

    def test_backward_compat_no_pstn_arg(self, store):
        store.upsert_object(_analyzed(CanonicalLocation(
            canonical_id="location:hq", provenance=_prov(), name="HQ Office",
        )))
        webex_locs = [{"name": "HQ Office", "id": "loc-123"}]
        result = check_locations(store, webex_locs)
        assert result.status == CheckStatus.PASS
        assert "PSTN check" in result.detail


# ===================================================================
# Check 4: Trunks
# ===================================================================


class TestCheckTrunks:
    def test_pass_no_conflicts(self, store):
        store.upsert_object(_analyzed(CanonicalTrunk(
            canonical_id="trunk:lgw1", provenance=_prov(), name="HQ-LGW",
        )))
        webex_trunks = [{"name": "Other-Trunk", "id": "t-456"}]
        result = check_trunks(store, webex_trunks)
        assert result.status == CheckStatus.PASS

    def test_warn_name_conflict(self, store):
        store.upsert_object(_analyzed(CanonicalTrunk(
            canonical_id="trunk:lgw1", provenance=_prov(), name="HQ-LGW",
        )))
        webex_trunks = [{"name": "HQ-LGW", "id": "t-789"}]
        result = check_trunks(store, webex_trunks)
        assert result.status == CheckStatus.WARN

    def test_skip_no_trunks(self, store):
        result = check_trunks(store, [])
        assert result.status == CheckStatus.SKIP


# ===================================================================
# Check 5: Feature Entitlements
# ===================================================================


class TestCheckFeatureEntitlements:
    def test_pass_within_limits(self, store):
        store.upsert_object(_analyzed(CanonicalHuntGroup(
            canonical_id="hunt_group:hg1", provenance=_prov(), name="Sales HG",
        )))
        existing = {"hunt_group": 5, "auto_attendant": 0, "call_queue": 0, "paging_group": 0}
        result = check_feature_entitlements(store, existing)
        assert result.status == CheckStatus.PASS

    def test_warn_approaching_limit(self, store):
        for i in range(200):
            store.upsert_object(_analyzed(CanonicalHuntGroup(
                canonical_id=f"hunt_group:hg{i}", provenance=_prov(), name=f"HG-{i}",
            )))
        existing = {"hunt_group": 850, "auto_attendant": 0, "call_queue": 0, "paging_group": 0}
        result = check_feature_entitlements(store, existing)
        assert result.status == CheckStatus.WARN

    def test_skip_no_features(self, store):
        existing = {"hunt_group": 0, "auto_attendant": 0, "call_queue": 0, "paging_group": 0}
        result = check_feature_entitlements(store, existing)
        assert result.status == CheckStatus.SKIP


# ===================================================================
# Check 6: Number Conflicts
# ===================================================================


class TestCheckNumberConflicts:
    def test_pass_no_conflicts(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))
        webex_numbers = [{"phoneNumber": "+14155559999", "owner": {"id": "p-1", "type": "PEOPLE"}}]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.PASS
        assert len(decisions) == 0

    def test_warn_e164_conflict(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))
        webex_numbers = [{
            "phoneNumber": "+14155551234",
            "owner": {"id": "p-existing", "type": "PEOPLE", "lastName": "Bob"},
        }]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1
        assert decisions[0]["type"] == "NUMBER_CONFLICT"
        assert decisions[0]["context"]["conflict_type"] == "E164"

    def test_extension_conflict_same_location(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            extension="1001",
            location_id="loc-123",
        )))
        webex_numbers = [{
            "extension": "1001",
            "location": {"id": "loc-123", "name": "HQ"},
            "owner": {"id": "p-existing", "type": "PEOPLE", "lastName": "Charlie"},
        }]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1
        assert decisions[0]["context"]["conflict_type"] == "EXTENSION"

    def test_line_e164_conflict(self, store):
        store.upsert_object(_analyzed(CanonicalLine(
            canonical_id="line:dn1", provenance=_prov(),
            e164="+14155551234", extension="1234",
        )))
        webex_numbers = [{
            "phoneNumber": "+14155551234",
            "owner": {"id": "p-existing", "type": "PEOPLE"},
        }]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1

    def test_workspace_phone_number_conflict(self, store):
        store.upsert_object(_analyzed(CanonicalWorkspace(
            canonical_id="workspace:001", provenance=_prov(),
            display_name="Lobby", phone_number="+14155551234",
        )))
        webex_numbers = [{
            "phoneNumber": "+14155551234",
            "owner": {"id": "p-existing", "type": "PEOPLE"},
        }]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1

    def test_no_conflict_when_same_email_owns_number(self, store):
        """Same-owner collisions are handled by DUPLICATE_USER, not NUMBER_CONFLICT.
        (from 05a-preflight-checks.md lines 403-409)
        """
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))
        webex_numbers = [{
            "phoneNumber": "+14155551234",
            "owner": {"id": "p-existing", "type": "PEOPLE", "email": "alice@test.com"},
        }]
        result, decisions = check_number_conflicts(store, webex_numbers)
        assert result.status == CheckStatus.PASS
        assert len(decisions) == 0

    def test_decision_has_fingerprint(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"],
            phone_numbers=[{"type": "work", "value": "+14155551234"}],
        )))
        webex_numbers = [{
            "phoneNumber": "+14155551234",
            "owner": {"id": "p-existing", "type": "PEOPLE"},
        }]
        _, decisions = check_number_conflicts(store, webex_numbers)
        assert "fingerprint" in decisions[0]
        assert len(decisions[0]["fingerprint"]) == 16


# ===================================================================
# Check 7: Duplicate Users
# ===================================================================


class TestCheckDuplicateUsers:
    def test_pass_no_duplicates(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["alice@test.com"],
        )))
        webex_people = [{"emails": ["bob@test.com"], "id": "p-1", "displayName": "Bob"}]
        result, decisions = check_duplicate_users(store, webex_people)
        assert result.status == CheckStatus.PASS
        assert len(decisions) == 0

    def test_warn_user_exists_no_calling(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["alice@test.com"],
        )))
        webex_people = [{"emails": ["alice@test.com"], "id": "p-1", "displayName": "Alice"}]
        result, decisions = check_duplicate_users(store, webex_people)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1
        assert decisions[0]["severity"] == "MEDIUM"
        assert decisions[0]["context"]["scenario"] == "exists_no_calling"

    def test_warn_user_exists_with_calling(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"], location_id="loc-123",
        )))
        webex_people = [{
            "emails": ["alice@test.com"], "id": "p-1",
            "displayName": "Alice", "locationId": "loc-123",
        }]
        result, decisions = check_duplicate_users(store, webex_people)
        assert result.status == CheckStatus.WARN
        assert len(decisions) == 1
        assert decisions[0]["severity"] == "HIGH"
        assert decisions[0]["context"]["scenario"] == "already_calling"
        assert decisions[0]["context"]["location_matches"] is True

    def test_case_insensitive_email_match(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["Alice@Test.com"],
        )))
        webex_people = [{"emails": ["alice@test.com"], "id": "p-1"}]
        result, decisions = check_duplicate_users(store, webex_people)
        assert result.status == CheckStatus.WARN

    def test_different_location_high_severity(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(),
            emails=["alice@test.com"], location_id="loc-planned",
        )))
        webex_people = [{
            "emails": ["alice@test.com"], "id": "p-1",
            "locationId": "loc-different",
        }]
        result, decisions = check_duplicate_users(store, webex_people)
        assert decisions[0]["context"]["location_matches"] is False
        # already_calling at different location → has "fail" option
        option_ids = [o["id"] for o in decisions[0]["options"]]
        assert "fail" in option_ids

    def test_decision_has_fingerprint(self, store):
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["alice@test.com"],
        )))
        webex_people = [{"emails": ["alice@test.com"], "id": "p-1"}]
        _, decisions = check_duplicate_users(store, webex_people)
        assert "fingerprint" in decisions[0]
        assert len(decisions[0]["fingerprint"]) == 16


# ===================================================================
# Check 8: Rate Limit Budget
# ===================================================================


class TestCheckRateLimitBudget:
    def test_pass_fast_migration(self, store):
        # Seed object first (FK constraint)
        store.upsert_object(_analyzed(CanonicalUser(
            canonical_id="user:001", provenance=_prov(), emails=["a@test.com"],
        )))
        store.conn.execute(
            "INSERT INTO plan_operations (node_id, canonical_id, op_type, resource_type, tier, api_calls, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("n1", "user:001", "create", "user", 2, 5, "pending"),
        )
        store.conn.commit()
        config = {"rate_limit_per_minute": 100, "max_migration_hours": 8}
        result = check_rate_limit_budget(store, config)
        assert result.status == CheckStatus.PASS

    def test_warn_long_migration(self, store):
        # Insert many operations to exceed max_hours — seed objects first (FK)
        for i in range(10000):
            store.conn.execute(
                "INSERT OR IGNORE INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                (f"user:{i:05d}", "user", "analyzed", "{}"),
            )
            store.conn.execute(
                "INSERT INTO plan_operations (node_id, canonical_id, op_type, resource_type, tier, api_calls, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"n{i}", f"user:{i:05d}", "create", "user", 2, 5, "pending"),
            )
        store.conn.commit()
        config = {"rate_limit_per_minute": 100, "max_migration_hours": 8}
        result = check_rate_limit_budget(store, config)
        assert result.status == CheckStatus.WARN

    def test_skip_no_operations(self, store):
        config = {"rate_limit_per_minute": 100, "max_migration_hours": 8}
        result = check_rate_limit_budget(store, config)
        assert result.status == CheckStatus.SKIP
