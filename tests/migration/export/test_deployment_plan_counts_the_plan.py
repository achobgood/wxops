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

    # 4 devices in inventory; only 2 get a create op.
    for i in range(4):
        dev = CanonicalDevice(
            canonical_id=f"device:d{i}",
            provenance=_prov(),
            name=f"SEP00000000000{i}",
            model="Cisco 8845",
            mac_address=f"00000000000{i}",
            owner_canonical_id=f"user:u{i % 3}",
            compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
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


class TestExcludedPopulationIsDisclosed:
    def test_document_names_the_excluded_objects(self, inventory_larger_than_plan):
        """"skip", "excluded", "incompatible" and "stale" appeared nowhere."""
        doc = generate_plan_summary(inventory_larger_than_plan, "proj").lower()
        assert "excluded" in doc or "not in this plan" in doc

    def test_excluded_counts_are_stated(self, inventory_larger_than_plan):
        doc = generate_plan_summary(inventory_larger_than_plan, "proj")
        # 2 users and 2 devices in the inventory produce no operation.
        assert "Person" in doc and "Device" in doc
        lowered = doc.lower()
        idx = lowered.find("not in this plan")
        if idx == -1:
            idx = lowered.find("excluded")
        assert idx != -1
        tail = doc[idx:]
        assert "2" in tail, "the excluded counts must be quantified, not just mentioned"


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
