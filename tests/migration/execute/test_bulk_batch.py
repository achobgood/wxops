"""Tests for batch partitioning with tier 8 bulk_rebuild_phones ops."""

from __future__ import annotations

import networkx as nx

from wxcli.migration.execute.batch import partition_into_batches


def _add_op(G, node_id, *, tier, batch, resource_type, op_type):
    G.add_node(
        node_id,
        canonical_id=node_id.rsplit(":", 1)[0],
        op_type=op_type,
        resource_type=resource_type,
        tier=tier,
        batch=batch,
        api_calls=1,
        description=f"{resource_type}:{op_type}",
        status="pending",
    )


def test_tier_8_rebuild_lands_in_per_site_batch():
    G = nx.DiGraph()
    _add_op(G, "device:d1:create", tier=3, batch="location:loc-1",
            resource_type="device", op_type="create")
    _add_op(G, "bulk_device_settings:location:loc-1:submit",
            tier=5, batch="location:loc-1",
            resource_type="bulk_device_settings", op_type="submit")
    _add_op(G, "bulk_rebuild_phones:location:loc-1:submit",
            tier=8, batch="location:loc-1",
            resource_type="bulk_rebuild_phones", op_type="submit")
    G.add_edge("device:d1:create", "bulk_device_settings:location:loc-1:submit")
    G.add_edge(
        "bulk_device_settings:location:loc-1:submit",
        "bulk_rebuild_phones:location:loc-1:submit",
    )

    batches = partition_into_batches(G)

    # No batch named "fixups" should exist when no ops have batch="fixups".
    assert all(b.site != "fixups" for b in batches)

    # Tier 8 rebuild op is in a batch with site=location:loc-1.
    rebuild_batches = [
        b for b in batches
        if b.tier == 8 and b.site == "location:loc-1"
    ]
    assert len(rebuild_batches) == 1
    assert "bulk_rebuild_phones:location:loc-1:submit" in rebuild_batches[0].operations

    # Tier ordering — rebuild batch comes after tier 5 bulk settings batch.
    def idx(predicate):
        for i, b in enumerate(batches):
            if predicate(b):
                return i
        return -1

    tier5_idx = idx(lambda b: b.tier == 5 and b.site == "location:loc-1")
    tier8_idx = idx(lambda b: b.tier == 8 and b.site == "location:loc-1")
    assert tier5_idx < tier8_idx


def test_fixups_batch_still_works_for_cycle_breakers():
    G = nx.DiGraph()
    _add_op(G, "user:u1:configure_settings", tier=7, batch="fixups",
            resource_type="user", op_type="configure_settings")

    batches = partition_into_batches(G)

    fixup_batches = [b for b in batches if b.site == "fixups"]
    assert len(fixup_batches) == 1
    assert fixup_batches[0].tier == 7
