"""Tests for Phase 12a planner fixes (Fixes 12, 13, 14).

Fix 12: User plan reduced to 3 ops (create, configure_settings, configure_voicemail).
        Extension and license included at creation time.
Fix 13: Location plan has enable_calling op. User->location dependency targets
        enable_calling (not create). DAG validates with no cycles.
Fix 14: Workspace license preflight matches "Webex Calling - Workspaces" but
        NOT "Webex Calling - Common Area".
"""

import pytest
from datetime import datetime, timezone

from wxcli.migration.models import (
    CanonicalUser,
    CanonicalLocation,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.execute.planner import (
    expand_to_operations,
    _expand_user,
    _expand_location,
)
from wxcli.migration.execute.dependency import build_dependency_graph, validate_tiers
from wxcli.migration.preflight.checks import check_workspace_licenses
from wxcli.migration.preflight import CheckStatus


@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _set_analyzed(obj):
    obj.status = MigrationStatus.ANALYZED
    return obj


# ---------------------------------------------------------------------------
# Fix 12: User plan reduced to 3 ops
# ---------------------------------------------------------------------------


class TestFix12UserOps:
    """User expansion: create always, configure_settings/voicemail only when data exists."""

    def test_user_without_settings_produces_1_op(self):
        """User with no custom settings → only create op."""
        obj = {
            "canonical_id": "user:test",
            "emails": ["test@acme.com"],
            "location_id": "location:hq",
            "extension": "1001",
        }
        ops = _expand_user(obj)
        assert len(ops) == 1
        assert ops[0].op_type == "create"

    def test_user_with_settings_produces_2_ops(self):
        """User with call_settings → create + configure_settings."""
        obj = {
            "canonical_id": "user:test",
            "emails": ["test@acme.com"],
            "location_id": "location:hq",
            "extension": "1001",
            "call_settings": {"call_forwarding": {"enabled": True}},
        }
        ops = _expand_user(obj)
        assert len(ops) == 2
        op_types = [op.op_type for op in ops]
        assert op_types == ["create", "configure_settings"]

    def test_user_with_voicemail_produces_2_ops(self):
        """User with voicemail settings → create + configure_voicemail."""
        obj = {
            "canonical_id": "user:test",
            "emails": ["test@acme.com"],
            "location_id": "location:hq",
            "extension": "1001",
            "voicemail": {"enabled": True, "rings": 4},
        }
        ops = _expand_user(obj)
        assert len(ops) == 2
        op_types = [op.op_type for op in ops]
        assert op_types == ["create", "configure_voicemail"]

    def test_user_with_both_produces_3_ops(self):
        """User with both settings and voicemail → 3 ops."""
        obj = {
            "canonical_id": "user:test",
            "emails": ["test@acme.com"],
            "location_id": "location:hq",
            "extension": "1001",
            "call_settings": {"dnd": True},
            "voicemail": {"enabled": True},
        }
        ops = _expand_user(obj)
        assert len(ops) == 3
        op_types = [op.op_type for op in ops]
        assert op_types == ["create", "configure_settings", "configure_voicemail"]

    def test_no_assign_number_or_assign_license_ops(self):
        """User plan must NOT contain user:assign_number or user:assign_license."""
        obj = {
            "canonical_id": "user:test",
            "emails": ["test@acme.com"],
            "location_id": "location:hq",
            "extension": "1001",
        }
        ops = _expand_user(obj)
        op_types = {op.op_type for op in ops}
        assert "assign_number" not in op_types
        assert "assign_license" not in op_types

    def test_user_ops_via_full_pipeline(self, store):
        """expand_to_operations for a user without settings → 1 op."""
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:pipeline",
            provenance=_prov(),
            emails=["pipeline@acme.com"],
            location_id="location:hq",
            extension="2001",
        ))
        store.upsert_object(user)
        ops = expand_to_operations(store)
        assert len(ops) == 1
        assert ops[0].op_type == "create"

    def test_user_configure_settings_depends_on_create(self):
        """configure_settings depends on create when present."""
        obj = {
            "canonical_id": "user:dep",
            "emails": ["dep@acme.com"],
            "location_id": "location:hq",
            "extension": "3001",
            "call_settings": {"forwarding": True},
        }
        ops = _expand_user(obj)
        by_op = {op.op_type: op for op in ops}
        assert "user:dep:create" in by_op["configure_settings"].depends_on

    def test_user_configure_voicemail_depends_on_create(self):
        """configure_voicemail depends on create when present."""
        obj = {
            "canonical_id": "user:dep",
            "emails": ["dep@acme.com"],
            "location_id": "location:hq",
            "extension": "3001",
            "voicemail": {"enabled": True},
        }
        ops = _expand_user(obj)
        by_op = {op.op_type: op for op in ops}
        assert "user:dep:create" in by_op["configure_voicemail"].depends_on


# ---------------------------------------------------------------------------
# Fix 13: Location plan has enable_calling
# ---------------------------------------------------------------------------


class TestFix13LocationEnableCalling:
    """Location expansion produces 2 ops: create + enable_calling."""

    def test_expand_location_produces_2_ops(self):
        """_expand_location returns 2 ops: create and enable_calling."""
        obj = {"canonical_id": "location:hq", "name": "HQ"}
        ops = _expand_location(obj)
        assert len(ops) == 2
        op_types = [op.op_type for op in ops]
        assert op_types == ["create", "enable_calling"]

    def test_enable_calling_depends_on_create(self):
        """enable_calling op depends on create op."""
        obj = {"canonical_id": "location:hq", "name": "HQ"}
        ops = _expand_location(obj)
        enable_op = [op for op in ops if op.op_type == "enable_calling"][0]
        assert "location:hq:create" in enable_op.depends_on

    def test_user_location_dependency_targets_enable_calling_in_dag(self, store):
        """User->location cross-ref dependency targets enable_calling, not create."""
        loc = _set_analyzed(CanonicalLocation(
            canonical_id="location:hq",
            provenance=_prov(),
            name="HQ",
        ))
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:u1",
            provenance=_prov(),
            emails=["u1@acme.com"],
            location_id="location:hq",
            extension="1001",
        ))
        store.upsert_object(loc)
        store.upsert_object(user)

        # Add cross-ref: user is in location
        store.add_cross_ref("user:u1", "location:hq", "user_in_location")

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        # The user:create node should have an edge from location:hq:enable_calling
        # (not location:hq:create)
        predecessors = list(G.predecessors("user:u1:create"))
        assert "location:hq:enable_calling" in predecessors
        # location:hq:create should NOT directly feed into user:u1:create
        # (it feeds into enable_calling, which feeds into user:create)
        assert "location:hq:create" not in predecessors

    def test_dag_validates_no_cycles(self, store):
        """Full DAG with location + user validates cleanly (no tier violations, no cycles)."""
        loc = _set_analyzed(CanonicalLocation(
            canonical_id="location:hq",
            provenance=_prov(),
            name="HQ",
        ))
        user = _set_analyzed(CanonicalUser(
            canonical_id="user:u1",
            provenance=_prov(),
            emails=["u1@acme.com"],
            location_id="location:hq",
            extension="1001",
        ))
        store.upsert_object(loc)
        store.upsert_object(user)
        store.add_cross_ref("user:u1", "location:hq", "user_in_location")

        ops = expand_to_operations(store)
        G = build_dependency_graph(ops, store)

        # No tier violations
        violations = validate_tiers(G)
        assert violations == []

        # DAG is acyclic
        import networkx as nx
        assert nx.is_directed_acyclic_graph(G)

    def test_location_via_full_pipeline(self, store):
        """expand_to_operations for a single location produces exactly 2 ops."""
        loc = _set_analyzed(CanonicalLocation(
            canonical_id="location:branch",
            provenance=_prov(),
            name="Branch Office",
        ))
        store.upsert_object(loc)
        ops = expand_to_operations(store)
        assert len(ops) == 2
        op_types = {op.op_type for op in ops}
        assert op_types == {"create", "enable_calling"}


# ---------------------------------------------------------------------------
# Fix 14: Workspace license preflight regression test
# ---------------------------------------------------------------------------


class TestFix14WorkspaceLicensePreflight:
    """check_workspace_licenses matches 'Webex Calling - Workspaces' but not 'Common Area'."""

    def test_matches_webex_calling_workspaces(self, store):
        """License named 'Webex Calling - Workspaces' should be found and matched."""
        # Add a workspace to the store so the check doesn't skip
        ws = _set_analyzed(CanonicalLocation(
            canonical_id="workspace:lobby",
            provenance=_prov(),
            name="Lobby",
        ))
        # We need to insert a workspace-type object; use raw SQL to set object_type
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("workspace:lobby", "workspace", "analyzed",
             '{"canonical_id":"workspace:lobby","display_name":"Lobby"}',
             "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        store.conn.commit()

        licenses = [
            {"name": "Webex Calling - Workspaces", "id": "lic-1",
             "totalUnits": 10, "consumedUnits": 0},
        ]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.PASS
        assert "1 needed" in result.detail

    def test_common_area_does_not_match(self, store):
        """License named 'Webex Calling - Common Area' should NOT match workspace check."""
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("workspace:lobby", "workspace", "analyzed",
             '{"canonical_id":"workspace:lobby","display_name":"Lobby"}',
             "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        store.conn.commit()

        licenses = [
            {"name": "Webex Calling - Common Area", "id": "lic-2",
             "totalUnits": 10, "consumedUnits": 0},
        ]
        result = check_workspace_licenses(store, licenses)
        # "Common Area" does NOT contain "workspace" so it should fail
        assert result.status == CheckStatus.FAIL
        assert "No Webex Calling Workspace licenses found" in result.detail

    def test_professional_workspaces_also_matches(self, store):
        """License named 'Webex Calling - Professional Workspaces' should also match."""
        store.conn.execute(
            "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("workspace:conf", "workspace", "analyzed",
             '{"canonical_id":"workspace:conf","display_name":"ConfRoom"}',
             "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        )
        store.conn.commit()

        licenses = [
            {"name": "Webex Calling - Professional Workspaces", "id": "lic-3",
             "totalUnits": 5, "consumedUnits": 2},
        ]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.PASS
        assert "1 needed, 3 available" in result.detail

    def test_no_workspaces_in_plan_skips(self, store):
        """When no workspaces in migration plan, check should skip."""
        licenses = [
            {"name": "Webex Calling - Workspaces", "id": "lic-1",
             "totalUnits": 10, "consumedUnits": 0},
        ]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.SKIP

    def test_insufficient_workspace_licenses(self, store):
        """When there aren't enough workspace licenses, check should fail."""
        # Add 3 workspaces
        for i in range(3):
            store.conn.execute(
                "INSERT INTO objects (canonical_id, object_type, status, data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (f"workspace:w{i}", "workspace", "analyzed",
                 f'{{"canonical_id":"workspace:w{i}","display_name":"W{i}"}}',
                 "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        store.conn.commit()

        licenses = [
            {"name": "Webex Calling - Workspaces", "id": "lic-1",
             "totalUnits": 2, "consumedUnits": 1},
        ]
        result = check_workspace_licenses(store, licenses)
        assert result.status == CheckStatus.FAIL
        assert "SHORT" in result.detail
