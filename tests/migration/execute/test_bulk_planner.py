"""Unit tests for the _optimize_for_bulk post-expansion pass."""

from __future__ import annotations

import pytest

from wxcli.migration.execute import MigrationOp
from wxcli.migration.execute.planner import _optimize_for_bulk
from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalDeviceLayout,
    DeviceCompatibilityTier,
    MigrationStatus,
)


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


class TestLineKeyTemplateAggregation:
    def test_groups_layouts_by_template_and_location(self, store, device_factory):
        # 120 devices in location loc-1, all using template tpl-a.
        # _optimize_for_bulk should emit 1 bulk_line_key_template op.
        for i in range(120):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            layout = CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-a",
                resolved_line_keys=[{"lineKeyType": "PRIMARY_LINE", "lineKeyIndex": 1}],
            )
            store.upsert_object(layout)

        ops = []
        for i in range(120):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(f"device_layout:d{i}", "configure", "device_layout", tier=7))

        result = _optimize_for_bulk(ops, store, threshold=100)

        # Layout ops removed.
        layout_ops = [
            o for o in result
            if o.resource_type == "device_layout" and o.op_type == "configure"
        ]
        assert layout_ops == []

        # One bulk_line_key_template op.
        bulk_lkt = [
            o for o in result
            if o.resource_type == "bulk_line_key_template" and o.op_type == "submit"
        ]
        assert len(bulk_lkt) == 1
        op = bulk_lkt[0]
        assert op.tier == 7
        assert "tpl-a" in op.canonical_id
        assert "location:loc-1" in op.canonical_id

    def test_splits_by_template_and_location(self, store, device_factory):
        # 120 devices, 2 templates, 2 locations → 4 bulk ops.
        for i in range(30):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-a",
                resolved_line_keys=[{"lineKeyIndex": 1}],
            ))
        for i in range(30, 60):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-b",
                resolved_line_keys=[{"lineKeyIndex": 1}],
            ))
        for i in range(60, 90):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-2")
            store.upsert_object(dev)
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-a",
                resolved_line_keys=[{"lineKeyIndex": 1}],
            ))
        for i in range(90, 120):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-2")
            store.upsert_object(dev)
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-b",
                resolved_line_keys=[{"lineKeyIndex": 1}],
            ))

        ops = []
        for i in range(120):
            loc = "location:loc-1" if i < 60 else "location:loc-2"
            ops.append(_op(f"device:d{i}", "create", "device", tier=3, batch=loc))
            ops.append(_op(f"device_layout:d{i}", "configure", "device_layout", tier=7))

        result = _optimize_for_bulk(ops, store, threshold=100)

        bulk_lkt = [
            o for o in result
            if o.resource_type == "bulk_line_key_template" and o.op_type == "submit"
        ]
        assert len(bulk_lkt) == 4
        identities = {op.canonical_id for op in bulk_lkt}
        assert identities == {
            "bulk_line_key_template:tpl-a:location:loc-1",
            "bulk_line_key_template:tpl-b:location:loc-1",
            "bulk_line_key_template:tpl-a:location:loc-2",
            "bulk_line_key_template:tpl-b:location:loc-2",
        }


from wxcli.migration.models import CanonicalSoftkeyConfig, Provenance


class TestDynamicSettingsAggregation:
    def test_groups_softkey_configs_by_location(self, store, device_factory):
        for i in range(110):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            store.upsert_object(CanonicalSoftkeyConfig(
                canonical_id=f"softkey_config:d{i}",
                device_canonical_id=f"device:d{i}",
                is_psk_target=True,
                psk_mappings=[{"psk": "PSK1", "fnc": "sd", "ext": "1000"}],
                provenance=dev.provenance,
            ))

        ops = []
        for i in range(110):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-1"))
            ops.append(_op(f"softkey_config:d{i}", "configure",
                            "softkey_config", tier=7))

        result = _optimize_for_bulk(ops, store, threshold=100)

        softkey_ops = [
            o for o in result
            if o.resource_type == "softkey_config" and o.op_type == "configure"
        ]
        assert softkey_ops == []

        bulk_dyn = [
            o for o in result
            if o.resource_type == "bulk_dynamic_settings" and o.op_type == "submit"
        ]
        assert len(bulk_dyn) == 1
        assert bulk_dyn[0].tier == 7
        assert bulk_dyn[0].batch == "location:loc-1"


class TestFallbackMetadata:
    """Verify _optimize_for_bulk stores fallback info in bulk payloads."""

    def test_device_settings_payload_includes_fallback_metadata(self, store):
        ops = []
        for i in range(120):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-1"))

        result = _optimize_for_bulk(ops, store, threshold=100)
        bulk_settings = [o for o in result if o.resource_type == "bulk_device_settings"]
        assert len(bulk_settings) == 1
        payload = bulk_settings[0].payload
        assert "covered_canonical_ids" in payload
        assert len(payload["covered_canonical_ids"]) == 120
        assert payload["fallback_handler_key"] == ["device", "configure_settings"]

    def test_line_key_template_payload_includes_fallback_metadata(self, store, device_factory):
        for i in range(120):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id=f"device_layout:d{i}",
                provenance=dev.provenance,
                device_canonical_id=f"device:d{i}",
                template_canonical_id="line_key_template:tpl-a",
                resolved_line_keys=[{"lineKeyIndex": 1}],
            ))

        ops = []
        for i in range(120):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-1"))
            ops.append(_op(f"device_layout:d{i}", "configure",
                            "device_layout", tier=7))

        result = _optimize_for_bulk(ops, store, threshold=100)
        bulk_lkt = [o for o in result if o.resource_type == "bulk_line_key_template"]
        assert len(bulk_lkt) == 1
        payload = bulk_lkt[0].payload
        assert "covered_canonical_ids" in payload
        assert len(payload["covered_canonical_ids"]) == 120
        assert payload["fallback_handler_key"] == ["device_layout", "configure"]

    def test_dynamic_settings_payload_includes_fallback_metadata(self, store, device_factory):
        for i in range(110):
            dev = device_factory(f"device:d{i}", location_cid="location:loc-1")
            store.upsert_object(dev)
            store.upsert_object(CanonicalSoftkeyConfig(
                canonical_id=f"softkey_config:d{i}",
                device_canonical_id=f"device:d{i}",
                is_psk_target=True,
                psk_mappings=[{"psk": "PSK1", "fnc": "sd", "ext": "1000"}],
                provenance=dev.provenance,
            ))

        ops = []
        for i in range(110):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-1"))
            ops.append(_op(f"softkey_config:d{i}", "configure",
                            "softkey_config", tier=7))

        result = _optimize_for_bulk(ops, store, threshold=100)
        bulk_dyn = [o for o in result if o.resource_type == "bulk_dynamic_settings"]
        assert len(bulk_dyn) == 1
        payload = bulk_dyn[0].payload
        assert "covered_canonical_ids" in payload
        assert len(payload["covered_canonical_ids"]) == 110
        assert payload["fallback_handler_key"] == ["softkey_config", "configure"]


class TestSkipRebuildPhones:
    """Verify skip_rebuild_phones suppresses rebuild ops."""

    def test_skip_rebuild_phones_omits_rebuild_ops(self, store):
        ops = []
        for i in range(120):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-1"))

        result = _optimize_for_bulk(ops, store, threshold=100,
                                      skip_rebuild_phones=True)
        rebuild = [o for o in result if o.resource_type == "bulk_rebuild_phones"]
        assert rebuild == []
        # Other bulk ops should still be present
        bulk_settings = [o for o in result if o.resource_type == "bulk_device_settings"]
        assert len(bulk_settings) == 1

    def test_skip_rebuild_phones_false_emits_rebuild(self, store):
        ops = []
        for i in range(120):
            cid = f"device:d{i}"
            ops.append(_op(cid, "create", "device", tier=3, batch="location:loc-1"))
            ops.append(_op(cid, "configure_settings", "device",
                            tier=5, batch="location:loc-1"))

        result = _optimize_for_bulk(ops, store, threshold=100,
                                      skip_rebuild_phones=False)
        rebuild = [o for o in result if o.resource_type == "bulk_rebuild_phones"]
        assert len(rebuild) == 1


class TestRebuildPhones:
    def test_emits_one_rebuild_op_per_location_at_tier_8(self, store, device_factory):
        # 120 devices across 2 locations. Expect 2 rebuild ops at tier 8.
        for i in range(60):
            store.upsert_object(device_factory(f"device:d{i}", location_cid="location:loc-1"))
        for i in range(60, 120):
            store.upsert_object(device_factory(f"device:d{i}", location_cid="location:loc-2"))

        ops = []
        for i in range(60):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-1"))
            ops.append(_op(f"device:d{i}", "configure_settings", "device",
                            tier=5, batch="location:loc-1"))
        for i in range(60, 120):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-2"))
            ops.append(_op(f"device:d{i}", "configure_settings", "device",
                            tier=5, batch="location:loc-2"))

        result = _optimize_for_bulk(ops, store, threshold=100)

        rebuild = [
            o for o in result
            if o.resource_type == "bulk_rebuild_phones" and o.op_type == "submit"
        ]
        assert len(rebuild) == 2
        assert all(o.tier == 8 for o in rebuild)
        assert {o.batch for o in rebuild} == {"location:loc-1", "location:loc-2"}

    def test_rebuild_depends_on_bulk_settings_ops(self, store, device_factory):
        for i in range(120):
            store.upsert_object(device_factory(f"device:d{i}", location_cid="location:loc-1"))

        ops = []
        for i in range(120):
            ops.append(_op(f"device:d{i}", "create", "device",
                            tier=3, batch="location:loc-1"))
            ops.append(_op(f"device:d{i}", "configure_settings", "device",
                            tier=5, batch="location:loc-1"))

        result = _optimize_for_bulk(ops, store, threshold=100)

        rebuild = [o for o in result if o.resource_type == "bulk_rebuild_phones"]
        assert len(rebuild) == 1
        dep_ids = set(rebuild[0].depends_on)
        assert "bulk_device_settings:location:loc-1:submit" in dep_ids


_TEST_PROVENANCE = Provenance(
    source_system="cucm",
    source_id="test-integration",
    source_name="test",
    extracted_at=__import__("datetime").datetime(2026, 1, 1,
                                                  tzinfo=__import__("datetime").timezone.utc),
)


class TestExpandToOperationsIntegration:
    def test_expand_above_threshold_produces_bulk_ops(self, store, device_factory):
        from wxcli.migration.execute.planner import expand_to_operations
        from wxcli.migration.models import (
            CanonicalLocation,
            CanonicalUser,
            LocationAddress,
            MigrationStatus,
        )

        loc = "location:loc-1"
        store.upsert_object(CanonicalLocation(
            canonical_id=loc, name="Loc 1",
            provenance=_TEST_PROVENANCE,
            address=LocationAddress(
                address1="1 Main", city="SF", state="CA",
                postal_code="94105", country="US",
            ),
            time_zone="America/Los_Angeles",
            preferred_language="en_us",
            announcement_language="en_us",
            status=MigrationStatus.ANALYZED,
        ))

        # 105 users each with a device in the same location.
        for i in range(105):
            u = CanonicalUser(
                canonical_id=f"user:u{i}",
                provenance=_TEST_PROVENANCE,
                emails=[f"u{i}@example.com"],
                display_name=f"User {i}",
                status=MigrationStatus.ANALYZED,
            )
            store.upsert_object(u)
            dev = device_factory(
                f"device:d{i}", location_cid=loc, owner_cid=f"user:u{i}",
            )
            dev.status = MigrationStatus.ANALYZED
            store.upsert_object(dev)

        ops = expand_to_operations(store, bulk_device_threshold=100)

        # Per-device settings ops gone.
        per_dev_settings = [
            o for o in ops
            if o.resource_type == "device" and o.op_type == "configure_settings"
        ]
        assert per_dev_settings == []

        # One bulk_device_settings submission.
        bulk_settings = [
            o for o in ops
            if o.resource_type == "bulk_device_settings"
        ]
        assert len(bulk_settings) == 1

        # Device creates preserved.
        creates = [
            o for o in ops
            if o.resource_type == "device" and o.op_type == "create"
        ]
        assert len(creates) == 105

    def test_expand_below_threshold_is_per_device(self, store, device_factory):
        from wxcli.migration.execute.planner import expand_to_operations
        from wxcli.migration.models import (
            CanonicalLocation,
            CanonicalUser,
            LocationAddress,
            MigrationStatus,
        )

        loc = "location:loc-1"
        store.upsert_object(CanonicalLocation(
            canonical_id=loc, name="Loc 1",
            provenance=_TEST_PROVENANCE,
            address=LocationAddress(
                address1="1 Main", city="SF", state="CA",
                postal_code="94105", country="US",
            ),
            time_zone="America/Los_Angeles",
            preferred_language="en_us",
            announcement_language="en_us",
            status=MigrationStatus.ANALYZED,
        ))
        for i in range(50):
            u = CanonicalUser(
                canonical_id=f"user:u{i}",
                provenance=_TEST_PROVENANCE,
                emails=[f"u{i}@example.com"],
                display_name=f"User {i}",
                status=MigrationStatus.ANALYZED,
            )
            store.upsert_object(u)
            dev = device_factory(f"device:d{i}", location_cid=loc, owner_cid=f"user:u{i}")
            dev.status = MigrationStatus.ANALYZED
            store.upsert_object(dev)

        ops = expand_to_operations(store, bulk_device_threshold=100)
        per_dev_settings = [
            o for o in ops
            if o.resource_type == "device" and o.op_type == "configure_settings"
        ]
        assert len(per_dev_settings) == 50
        bulk_settings = [o for o in ops if o.resource_type == "bulk_device_settings"]
        assert bulk_settings == []
