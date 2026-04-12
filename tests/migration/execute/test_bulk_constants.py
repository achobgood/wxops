"""Smoke test for bulk-operation constants in execute/__init__.py."""


def test_bulk_constants_registered():
    from wxcli.migration.execute import (
        API_CALL_ESTIMATES,
        BULK_DEVICE_THRESHOLD_DEFAULT,
        BULK_JOB_TYPES,
        SERIALIZED_RESOURCE_TYPES,
        TIER_ASSIGNMENTS,
    )

    assert BULK_DEVICE_THRESHOLD_DEFAULT == 100
    for rt in ("bulk_device_settings", "bulk_line_key_template",
               "bulk_dynamic_settings", "bulk_rebuild_phones"):
        assert (rt, "submit") in TIER_ASSIGNMENTS
        assert f"{rt}:submit" in API_CALL_ESTIMATES
        assert rt in SERIALIZED_RESOURCE_TYPES
        assert rt in BULK_JOB_TYPES
    assert TIER_ASSIGNMENTS[("bulk_rebuild_phones", "submit")] == 8
