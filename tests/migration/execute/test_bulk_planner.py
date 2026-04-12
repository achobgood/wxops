"""Unit tests for the _optimize_for_bulk post-expansion pass."""

from __future__ import annotations

import pytest

from wxcli.migration.execute import MigrationOp
from wxcli.migration.execute.planner import _optimize_for_bulk


def _op(cid: str, op_type: str, resource_type: str, **kw) -> MigrationOp:
    return MigrationOp(
        canonical_id=cid,
        op_type=op_type,
        resource_type=resource_type,
        tier=kw.get("tier", 5),
        batch=kw.get("batch"),
        api_calls=kw.get("api_calls", 1),
        description=kw.get("description", f"{resource_type}:{op_type}"),
        depends_on=kw.get("depends_on", []),
    )


class TestBelowThreshold:
    def test_small_plan_returns_ops_unchanged(self, store):
        # 10 device:create + 10 device:configure_settings — total 10 devices.
        ops = []
        for i in range(10):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-1"))

        result = _optimize_for_bulk(ops, store, threshold=100)

        assert result == ops  # identity, no replacement

    def test_threshold_zero_forces_bulk(self, store):
        # Threshold 0 means "always bulk". Below-threshold branch must not
        # be taken even when device count is small.
        ops = [
            _op("device:d1", "create", "device", tier=3, batch="location:loc-1"),
            _op("device:d1", "configure_settings", "device",
                tier=5, batch="location:loc-1"),
        ]
        result = _optimize_for_bulk(ops, store, threshold=0)
        assert result != ops  # optimization ran


class TestDeviceSettingsAggregation:
    def test_groups_device_settings_by_location(self, store):
        # 120 devices spread across 2 locations (above threshold 100).
        ops = []
        for i in range(80):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-1"))
        for i in range(80, 120):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-2"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-2"))

        result = _optimize_for_bulk(ops, store, threshold=100)

        # All 120 device:create ops preserved (no bulk create API).
        creates = [o for o in result if o.resource_type == "device" and o.op_type == "create"]
        assert len(creates) == 120

        # All device:configure_settings ops gone.
        per_device_settings = [
            o for o in result
            if o.resource_type == "device" and o.op_type == "configure_settings"
        ]
        assert per_device_settings == []

        # One bulk_device_settings:submit per location.
        bulk_settings = [
            o for o in result
            if o.resource_type == "bulk_device_settings" and o.op_type == "submit"
        ]
        assert len(bulk_settings) == 2
        assert {o.batch for o in bulk_settings} == {"location:loc-1", "location:loc-2"}
        # All at tier 5.
        assert all(o.tier == 5 for o in bulk_settings)
