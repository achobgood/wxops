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

    @pytest.mark.xfail(
        reason="Bulk replacement added incrementally in Tasks 8-11",
        strict=True,
    )
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
