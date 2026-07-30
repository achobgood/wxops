"""Tests for deployment_plan — generates summary-only deployment plan.

Phase 12b: summary plan with 8 sections, no CLI commands, no placeholders.
"""

import re
import pytest
from datetime import datetime, timezone

import networkx as nx

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.export.deployment_plan import (
    generate_plan_summary,
    _section_objective,
    _section_prerequisites,
    _section_resource_summary,
    _section_decisions,
    _section_batch_order,
    _section_impact,
    _section_rollback_strategy,
    _section_approval,
    _count_planned_by_type,
    WEBEX_RESOURCE_TYPES,
)
from wxcli.migration.models import (
    CanonicalLocation,
    CanonicalUser,
    CanonicalDevice,
    CanonicalHuntGroup,
    MigrationStatus,
    Provenance,
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


def _build_sample_plan(store):
    """Create a small plan with location + user + hunt_group."""
    loc = _analyzed(CanonicalLocation(
        canonical_id="location:hq",
        provenance=_prov(),
        name="HQ",
        time_zone="America/New_York",
        preferred_language="en_US",
        announcement_language="en_us",
    ))
    user = _analyzed(CanonicalUser(
        canonical_id="user:jsmith",
        provenance=_prov(),
        emails=["jsmith@acme.com"],
        first_name="John",
        last_name="Smith",
        location_id="location:hq",
        extension="1001",
    ))
    hg = _analyzed(CanonicalHuntGroup(
        canonical_id="hunt_group:hg1",
        provenance=_prov(),
        name="Sales HG",
        extension="2001",
        location_id="location:hq",
    ))
    store.upsert_object(loc)
    store.upsert_object(user)
    store.upsert_object(hg)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq", op_type="create",
               resource_type="location", tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    G.add_node("user:jsmith:create", canonical_id="user:jsmith", op_type="create",
               resource_type="user", tier=2, batch="site:hq", api_calls=1,
               description="Create user jsmith@acme.com")
    G.add_node("hunt_group:hg1:create", canonical_id="hunt_group:hg1",
               op_type="create", resource_type="hunt_group", tier=4,
               batch="site:hq", api_calls=1,
               description="Create hunt group Sales HG")

    G.add_edge("location:hq:create", "user:jsmith:create",
               type=DependencyType.REQUIRES)
    G.add_edge("user:jsmith:create", "hunt_group:hg1:create",
               type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)
    return G


# ---------------------------------------------------------------------------
# Full plan generation
# ---------------------------------------------------------------------------

class TestGeneratePlanSummary:
    def test_all_eight_sections_present(self, store):
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")

        assert "## 1. Objective" in plan
        assert "## 2. Prerequisites" in plan
        assert "## 3. Resource Summary" in plan
        assert "## 4. Decisions Made" in plan
        assert "## 5. Batch Execution Order" in plan
        assert "## 6. Estimated Impact" in plan
        assert "## 7. Rollback Strategy" in plan
        assert "## 8. Approval" in plan

    def test_header_format(self, store):
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")

        assert plan.startswith("# Deployment Plan: CUCM Migration")
        assert "Created:" in plan
        assert "Agent: wxc-calling-builder" in plan

    def test_no_cli_commands_in_summary(self, store):
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")

        assert "wxcli locations create" not in plan
        assert "wxcli users create" not in plan
        assert "{STEP_" not in plan
        assert "{CALLING_LICENSE_ID}" not in plan

    def test_resource_summary_excludes_cucm_types(self, store):
        """CUCM-only types should not appear in the resource summary."""
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")

        # These CUCM-only types should not appear
        assert "partition" not in plan.lower().split("## 4.")[0]  # Only check section 3
        assert "css" not in plan.lower().split("## 4.")[0]
        assert "device_pool" not in plan.lower().split("## 4.")[0]

    def test_decisions_section_shows_resolved(self, store):
        _build_sample_plan(store)
        # Add a resolved decision
        store.save_decision({
            "decision_id": "D0001",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "MEDIUM",
            "summary": "Cisco 7911 not supported",
            "context": {},
            "options": [{"id": "skip", "label": "Skip device"}],
            "chosen_option": "skip",
            "resolved_at": "2026-03-24T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-001",
            "run_id": "test",
        })
        plan = generate_plan_summary(store, "test-project")
        assert "D0001" in plan
        assert "DEVICE_INCOMPATIBLE" in plan

    def test_impact_section_shows_op_count(self, store):
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")

        assert "Total operations" in plan
        assert "3" in plan  # 3 ops in the plan

    def test_export_backwards_compat(self, store):
        """wxcli cucm export should still produce a summary."""
        _build_sample_plan(store)
        plan = generate_plan_summary(store, "test-project")
        # Should be valid markdown
        assert plan.strip().startswith("#")


# ---------------------------------------------------------------------------
# Section-level tests
# ---------------------------------------------------------------------------

class TestSectionObjective:
    def test_counts_in_objective(self):
        lines = _section_objective(
            {"user": 10, "device": 5, "location": 2, "hunt_group": 3},
            "proj-1",
        )
        text = "\n".join(lines)
        assert "10 users" in text
        assert "5 devices" in text
        assert "3 call features" in text

    def test_empty_counts(self):
        lines = _section_objective({}, "proj-1")
        text = "\n".join(lines)
        assert "migration objects" in text


class TestSectionPrerequisites:
    def test_no_pending_decisions(self):
        lines = _section_prerequisites({"user": 5}, 0)
        text = "\n".join(lines)
        assert "[x]" in text
        assert "Blockers found:** None" in text

    def test_pending_decisions(self):
        lines = _section_prerequisites({"user": 5}, 3)
        text = "\n".join(lines)
        assert "3 pending" in text
        assert "must be resolved" in text


class TestSectionResourceSummary:
    def test_includes_webex_types(self):
        counts = {"location": 2, "user": 10, "hunt_group": 3}
        lines = _section_resource_summary(counts)
        text = "\n".join(lines)
        assert "Location" in text
        assert "Person" in text
        assert "Hunt Group" in text

    def test_renders_every_planned_type_including_the_eight_it_used_to_drop(self):
        """The table is plan-derived, so nothing in it may be filtered out.

        Section 3 was scoped to WEBEX_RESOURCE_TYPES, which omitted 8 types /
        615 entities on director-demo-2026-04-15 — about a third of the plan.
        They were in the operation totals and Section 5's batch order, so the
        document was not wrong; the one table an approver reads as "what this
        builds" was.
        """
        counts = {
            "ecbn_config": 304, "device_layout": 215, "call_forwarding": 51,
            "line_key_template": 18, "bulk_line_key_template": 12,
            "bulk_rebuild_phones": 6, "bulk_device_settings": 6, "route_list": 3,
        }
        text = "\n".join(_section_resource_summary(counts))
        assert sum(counts.values()) == 615
        for count in counts.values():
            assert f"| {count} |" in text
        assert "Emergency Callback Number" in text
        assert "Device Line Key Layout" in text
        assert "Line Key Template (bulk job)" in text
        assert "Route List" in text

    def test_states_that_counts_are_resources_not_operations(self):
        text = "\n".join(_section_resource_summary({"user": 277}))
        assert "Distinct resources this plan acts on" in text
        assert "lower than the operation total in Section 6" in text

    def test_cucm_only_types_never_reach_the_table(self, tmp_path):
        """The invariant the old display filter stood in for.

        `partition` / `css` / `device_pool` are CUCM constructs consumed by
        mappers; no expander emits operations for them, so they cannot appear
        in `plan_operations`. Enforced here at the data source rather than by
        an allowlist on the renderer, which silently dropped real work and
        would need hand-extending for every new op type. Verified against
        dcloud-fresh and director-demo-2026-04-15: neither has a single
        CUCM-only row in plan_operations.
        """
        from datetime import datetime, timezone

        from wxcli.migration.models import (
            CanonicalLocation, MigrationObject, MigrationStatus, Provenance,
        )
        from wxcli.migration.store import MigrationStore

        store = MigrationStore(tmp_path / "migration.db")
        prov = Provenance(
            source_system="cucm", source_id="pk1", source_name="x",
            extracted_at=datetime.now(timezone.utc),
        )
        store.upsert_object(CanonicalLocation(
            canonical_id="location:hq", provenance=prov,
            status=MigrationStatus.ANALYZED, name="HQ",
            time_zone="America/New_York", preferred_language="en_US",
            announcement_language="en_us",
        ))
        # CUCM-only objects exist in the store and get no operations.
        for cid in ("partition:PT-Internal", "css:CSS-Internal", "device_pool:DP-HQ"):
            store.upsert_object(MigrationObject(
                canonical_id=cid, provenance=prov,
                status=MigrationStatus.ANALYZED,
            ))
        store.conn.execute(
            """INSERT INTO plan_operations
               (node_id, canonical_id, op_type, resource_type, tier, batch,
                api_calls, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("location:hq:create", "location:hq", "create", "location", 0,
             "org-wide", 1, "Create location HQ", "pending"),
        )
        store.conn.commit()
        try:
            counts = _count_planned_by_type(store)
        finally:
            store.close()

        assert counts == {"location": 1}
        for cucm_only in ("partition", "css", "device_pool"):
            assert cucm_only not in counts


class TestSectionDecisions:
    def test_no_decisions(self):
        lines = _section_decisions([])
        text = "\n".join(lines)
        assert "No decisions" in text

    def test_resolved_decisions_shown(self):
        decisions = [
            {
                "decision_id": "D0001",
                "type": "DEVICE_INCOMPATIBLE",
                "summary": "Phone 7911 not supported",
                "chosen_option": "skip",
                "options": [{"id": "skip", "label": "Skip device"}],
            },
        ]
        lines = _section_decisions(decisions)
        text = "\n".join(lines)
        assert "D0001" in text
        assert "DEVICE_INCOMPATIBLE" in text
        assert "Skip device" in text


class TestSectionBatchOrder:
    def test_batch_order_table(self):
        ops = [
            {"tier": 0, "batch": "org-wide", "resource_type": "location",
             "node_id": "a", "canonical_id": "a", "op_type": "create",
             "description": "", "api_calls": 1, "status": "pending"},
            {"tier": 2, "batch": "site:hq", "resource_type": "user",
             "node_id": "b", "canonical_id": "b", "op_type": "create",
             "description": "", "api_calls": 1, "status": "pending"},
        ]
        lines = _section_batch_order(ops)
        text = "\n".join(lines)
        assert "org-wide" in text
        assert "site:hq" in text

    def test_empty_ops(self):
        lines = _section_batch_order([])
        text = "\n".join(lines)
        assert "No operations planned" in text


class TestSectionImpact:
    def test_impact_counts(self):
        lines = _section_impact({"user": 10, "device": 5, "workspace": 2}, 50, 100)
        text = "\n".join(lines)
        assert "10 new Webex Calling users" in text
        assert "5 devices" in text
        assert "2 new workspaces" in text
        assert "100 calls" in text
        assert "Total operations" in text
        assert "50" in text

    def test_no_licenses_when_no_users(self):
        lines = _section_impact({"trunk": 2}, 5, 10)
        text = "\n".join(lines)
        assert "Licenses consumed" not in text


class TestSectionRollbackStrategy:
    def test_static_text(self):
        lines = _section_rollback_strategy()
        text = "\n".join(lines)
        assert "reverse dependency order" in text
        assert "wxcli cucm rollback" in text


class TestSectionApproval:
    def test_approval_checkboxes(self):
        lines = _section_approval()
        text = "\n".join(lines)
        assert "- [ ] **I approve" in text
        assert "- [ ] **I need changes" in text
        assert "- [ ] **Cancel" in text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_plan(self, store):
        plan = generate_plan_summary(store, "empty-project")
        assert "## 1. Objective" in plan
        assert "## 8. Approval" in plan
        assert "No operations planned" in plan

    def test_single_location(self, store):
        loc = _analyzed(CanonicalLocation(
            canonical_id="location:only",
            provenance=_prov(),
            name="Only Location",
            time_zone="UTC",
            preferred_language="en_US",
            announcement_language="en_us",
        ))
        store.upsert_object(loc)

        G = nx.DiGraph()
        G.add_node("location:only:create", canonical_id="location:only",
                   op_type="create", resource_type="location", tier=0,
                   batch="org-wide", api_calls=1,
                   description="Create location Only Location")
        save_plan_to_store(G, store)

        plan = generate_plan_summary(store, "single-loc")
        assert "Location" in plan
        assert "Only Location" not in plan  # Name not in summary (only counts)
        # No executable CLI commands (wxcli references in prerequisites/rollback are fine)
        assert "wxcli locations create" not in plan
        assert "{STEP_" not in plan


# ---------------------------------------------------------------------------
# Activation Codes section
# ---------------------------------------------------------------------------

def test_deployment_plan_has_activation_codes_section_when_convertible_present(tmp_path):
    """Plans with create_activation_code ops include an Activation Codes section."""
    from wxcli.migration.models import (
        CanonicalDevice,
        CanonicalUser,
        DeviceCompatibilityTier,
        MigrationStatus,
        Provenance,
    )
    from wxcli.migration.store import MigrationStore
    from wxcli.migration.export.deployment_plan import generate_plan_summary
    from datetime import datetime, timezone

    store = MigrationStore(tmp_path / "plan.db")
    try:
        prov = Provenance(
            source_system="cucm",
            source_id="pk-test",
            source_name="test",
            extracted_at=datetime.now(timezone.utc),
        )
        user = CanonicalUser(
            canonical_id="user:alice",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            emails=["alice@acme.com"],
            display_name="Alice Smith",
        )
        device = CanonicalDevice(
            canonical_id="device:SEP001122AABBCC",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            mac="001122AABBCC",
            model="DMS Cisco 8851",
            compatibility_tier=DeviceCompatibilityTier.CONVERTIBLE,
            display_name="SEP001122AABBCC",
            owner_canonical_id="user:alice",
            location_canonical_id="location:hq",
        )
        store.upsert_object(user)
        store.upsert_object(device)
        store.conn.execute(
            """INSERT INTO plan_operations
               (node_id, canonical_id, op_type, resource_type, tier, batch,
                api_calls, description, status, webex_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "device:SEP001122AABBCC:create_activation_code",
                "device:SEP001122AABBCC",
                "create_activation_code",
                "device",
                3,
                "location:hq",
                1,
                "Generate activation code for SEP001122AABBCC",
                "pending",
                None,
            ),
        )
        store.conn.commit()

        md = generate_plan_summary(store, "test-project")
        assert "## Activation Codes" in md
        assert "SEP001122AABBCC" in md
        assert "Alice Smith" in md
        assert "DMS Cisco 8851" in md
    finally:
        store.close()


def test_deployment_plan_omits_activation_codes_section_when_none(tmp_path):
    """Plans with no convertible devices don't include an empty section."""
    from wxcli.migration.models import CanonicalLocation, MigrationStatus, Provenance
    from wxcli.migration.store import MigrationStore
    from wxcli.migration.export.deployment_plan import generate_plan_summary
    from datetime import datetime, timezone

    store = MigrationStore(tmp_path / "plan.db")
    try:
        prov = Provenance(
            source_system="cucm",
            source_id="pk-test",
            source_name="test",
            extracted_at=datetime.now(timezone.utc),
        )
        loc = CanonicalLocation(
            canonical_id="location:hq",
            provenance=prov,
            status=MigrationStatus.ANALYZED,
            name="HQ",
            time_zone="UTC",
            preferred_language="en_US",
            announcement_language="en_us",
        )
        store.upsert_object(loc)
        store.conn.execute(
            """INSERT INTO plan_operations
               (node_id, canonical_id, op_type, resource_type, tier, batch,
                api_calls, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "location:hq:create",
                "location:hq",
                "create",
                "location",
                0,
                "org-wide",
                1,
                "Create location HQ",
                "pending",
            ),
        )
        store.conn.commit()

        md = generate_plan_summary(store, "test-project")
        assert "## Activation Codes" not in md
    finally:
        store.close()
