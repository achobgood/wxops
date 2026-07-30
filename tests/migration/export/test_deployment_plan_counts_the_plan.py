"""The deployment plan must count the plan, not the object inventory (F03).

``_count_by_type`` ran ``COUNT(*) FROM objects`` with no status filter and no
plan filter, and fed Sections 1, 2, 3 and 6. On director-demo-2026-04-15 that
made Section 3 claim Device 1100 / Person 300 / Translation Pattern 17 /
Call Park 12 / Pickup Group 34 "Create" while ``plan_operations`` held 772
devices, 277 users, 0 translation patterns, 0 call parks and 17 pickup groups.

This is the document ``cucm-migrate/SKILL.md`` Step 3 presents at the
"Ready to execute? (yes/no)" gate, so approval was given against numbers that
overstated the migration — and the same file printed the true "Total operations"
lower down, contradicting itself with no hint which number was real.

The fixture below is that shape in miniature: an inventory strictly larger than
the plan, including two object types that produce no operations at all.
"""

from __future__ import annotations

from datetime import datetime, timezone

import networkx as nx
import pytest

from wxcli.migration.execute import DependencyType
from wxcli.migration.execute.batch import save_plan_to_store
from wxcli.migration.export.deployment_plan import generate_plan_summary
from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalLocation,
    CanonicalPickupGroup,
    CanonicalTranslationPattern,
    CanonicalUser,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


def _prov() -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture()
def inventory_larger_than_plan(tmp_path):
    """5 users in inventory, 3 planned. 4 devices, 2 planned. 2 types unplanned."""
    store = MigrationStore(tmp_path / "migration.db")

    loc = CanonicalLocation(
        canonical_id="location:hq",
        provenance=_prov(),
        name="HQ",
        time_zone="America/New_York",
        preferred_language="en_US",
        announcement_language="en_us",
    )
    loc.status = MigrationStatus.ANALYZED
    store.upsert_object(loc)

    # 3 users reach the plan, 2 are stranded at 'normalized' (the F08 shape).
    for i in range(5):
        user = CanonicalUser(
            canonical_id=f"user:u{i}",
            provenance=_prov(),
            emails=[f"u{i}@acme.com"],
            first_name="U",
            last_name=str(i),
            location_id="location:hq",
            extension=f"100{i}",
        )
        user.status = (
            MigrationStatus.ANALYZED if i < 3 else MigrationStatus.NORMALIZED
        )
        store.upsert_object(user)

    # 4 devices in inventory; only 2 get a create op. The remaining two are
    # deliberately different so all three "unplanned" buckets are exercised:
    #   d2 — webex_app, needs no operation by design (must NOT be a finding)
    #   d3 — native_mpp, analyzed, no operation, no known reason (must be one)
    tiers = [
        DeviceCompatibilityTier.NATIVE_MPP,
        DeviceCompatibilityTier.NATIVE_MPP,
        DeviceCompatibilityTier.WEBEX_APP,
        DeviceCompatibilityTier.NATIVE_MPP,
    ]
    for i in range(4):
        dev = CanonicalDevice(
            canonical_id=f"device:d{i}",
            provenance=_prov(),
            name=f"SEP00000000000{i}",
            model="Cisco 8845",
            mac_address=f"00000000000{i}",
            owner_canonical_id=f"user:u{i % 3}",
            compatibility_tier=tiers[i],
        )
        dev.status = MigrationStatus.ANALYZED
        store.upsert_object(dev)

    # Two types that exist in the inventory but produce NO operation at all —
    # exactly the translation_pattern / call_park case on the real projects.
    tp = CanonicalTranslationPattern(
        canonical_id="translation_pattern:tp1",
        provenance=_prov(),
        name="TP1",
        matching_pattern="9XXX",
        replacement_pattern="XXX",
    )
    tp.status = MigrationStatus.NORMALIZED
    store.upsert_object(tp)

    pg = CanonicalPickupGroup(
        canonical_id="pickup_group:pg1",
        provenance=_prov(),
        name="PG1",
        location_id="location:hq",
    )
    pg.status = MigrationStatus.NORMALIZED
    store.upsert_object(pg)

    G = nx.DiGraph()
    G.add_node("location:hq:create", canonical_id="location:hq", op_type="create",
               resource_type="location", tier=0, batch="org-wide", api_calls=1,
               description="Create location HQ")
    for i in range(3):
        G.add_node(f"user:u{i}:create", canonical_id=f"user:u{i}", op_type="create",
                   resource_type="user", tier=2, batch="site:hq", api_calls=1,
                   description=f"Create user u{i}@acme.com")
        G.add_edge("location:hq:create", f"user:u{i}:create",
                   type=DependencyType.REQUIRES)
    for i in range(2):
        G.add_node(f"device:d{i}:create", canonical_id=f"device:d{i}", op_type="create",
                   resource_type="device", tier=3, batch="site:hq", api_calls=1,
                   description=f"Create device d{i}")
        G.add_edge(f"user:u{i}:create", f"device:d{i}:create",
                   type=DependencyType.REQUIRES)

    save_plan_to_store(G, store)
    yield store
    store.close()


def test_fixture_inventory_really_exceeds_the_plan(inventory_larger_than_plan):
    """Guard the guard — equal counts would make every assertion below vacuous."""
    store = inventory_larger_than_plan
    inv = dict(store.conn.execute(
        "SELECT object_type, COUNT(*) FROM objects GROUP BY object_type"
    ).fetchall())
    plan = dict(store.conn.execute(
        "SELECT resource_type, COUNT(*) FROM plan_operations "
        "WHERE op_type='create' GROUP BY resource_type"
    ).fetchall())
    assert inv["user"] == 5 and plan["user"] == 3
    assert inv["device"] == 4 and plan["device"] == 2
    assert inv["translation_pattern"] == 1 and "translation_pattern" not in plan
    assert inv["pickup_group"] == 1 and "pickup_group" not in plan

    from wxcli.migration.export.deployment_plan import _classify_unplanned

    unplanned = _classify_unplanned(store)
    assert unplanned.stranded == {
        "user": 2, "translation_pattern": 1, "pickup_group": 1
    }
    assert unplanned.no_op_expected == {"device": 1}, "the webex_app device"
    assert unplanned.unexplained == {"device": 1}, "the analyzed native_mpp device"


class TestResourceSummaryReflectsThePlan:
    def test_person_count_is_the_planned_count(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Person | 3 |" in doc
        assert "| Person | 5 |" not in doc, "5 is the inventory, 3 is the plan"

    def test_device_count_is_the_planned_count(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Device | 2 |" in doc
        assert "| Device | 4 |" not in doc

    def test_unplanned_types_are_not_claimed_as_create(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Translation Pattern | 1 | Create |" not in doc
        assert "| Pickup Group | 1 | Create |" not in doc


class TestUnplannedObjectsAreDisclosedByReason:
    """A flat "excluded" count is its own misstatement.

    Measured on director-demo: of 328 devices with no operation, 314 are
    `webex_app` (softphones moving to the Webex App — nothing to provision) and
    13 are `infrastructure`. Calling those "excluded because a decision resolved
    to skip, the object is incompatible, or its decision was invalidated" puts a
    false claim in a customer-facing document.
    """

    def test_document_discloses_unplanned_objects(self, inventory_larger_than_plan):
        """"skip", "excluded", "incompatible" and "stale" appeared nowhere."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj").lower()
        assert "not in this plan" in doc

    def test_stranded_objects_are_flagged_with_the_right_reason(
        self, inventory_larger_than_plan
    ):
        """2 users never reached 'analyzed' — the finding-F08 population."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Person | 2 | Stopped advancing before the planner ran |" in doc

    def test_by_design_absences_are_not_called_excluded(
        self, inventory_larger_than_plan
    ):
        """The webex_app device needs no operation and must not be a finding."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        idx = doc.find("### Not in this plan")
        assert idx != -1
        table = doc[idx:doc.find("Investigate with", idx)]
        assert "Stopped advancing" in table
        # Exactly one device is a genuine finding (the analyzed native_mpp with
        # no op). The webex_app device must not be counted alongside it.
        assert "| Device | 1 | Analyzed, but produced no operation" in table
        assert "| Device | 2 |" not in table, (
            "the webex_app device must not be listed alongside genuine problems"
        )

    def test_by_design_absences_are_still_accounted_for(
        self, inventory_larger_than_plan
    ):
        """Stated so the arithmetic reconciles — but with no call to action."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "require no operation" in doc
        assert "No action needed" in doc

    def test_unexplained_absence_is_flagged(self, inventory_larger_than_plan):
        """1 analyzed native_mpp device produced no op for no known reason."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "no known reason" in doc

    def test_no_disclosure_section_when_the_plan_is_complete(self, tmp_path):
        """A plan that covers everything must not grow an empty warning block."""
        store = MigrationStore(tmp_path / "complete.db")
        loc = CanonicalLocation(
            canonical_id="location:hq",
            provenance=_prov(),
            name="HQ",
            time_zone="America/New_York",
            preferred_language="en_US",
            announcement_language="en_us",
        )
        loc.status = MigrationStatus.ANALYZED
        store.upsert_object(loc)
        G = nx.DiGraph()
        G.add_node("location:hq:create", canonical_id="location:hq", op_type="create",
                   resource_type="location", tier=0, batch="org-wide", api_calls=1,
                   description="Create location HQ")
        save_plan_to_store(G, store)
        doc = generate_plan_summary(store, "proj")
        store.close()
        assert "### Not in this plan" not in doc
        assert "no known reason" not in doc


class TestImpactSectionReflectsThePlan:
    def test_licenses_consumed_uses_planned_users(self, inventory_larger_than_plan):
        """A commercial number the customer reads — 5 licences for 3 users."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Users added | 3 new Webex Calling users |" in doc
        assert "5 new Webex Calling users" not in doc
        assert "3 Webex Calling Professional" in doc
        assert "5 Webex Calling Professional" not in doc

    def test_devices_provisioned_uses_planned_devices(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "| Devices provisioned | 2 devices |" in doc
        assert "4 devices |" not in doc


class TestObjectiveReflectsThePlan:
    def test_objective_states_planned_counts(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        assert "3 users" in doc
        assert "5 users" not in doc


class TestDocumentDoesNotContradictItself:
    def test_resource_counts_reconcile_with_total_operations(
        self, inventory_larger_than_plan
    ):
        """The old document printed the true total beside inflated per-type counts."""
        store = inventory_larger_than_plan
        doc = generate_plan_summary(store, "proj")
        total_ops = store.conn.execute(
            "SELECT COUNT(*) FROM plan_operations"
        ).fetchone()[0]
        assert f"| Total operations | {total_ops} |" in doc
        # 1 location + 3 users + 2 devices = 6 create ops = the whole plan here.
        assert total_ops == 6
