"""Planner expansion for device_settings_template objects."""
from datetime import datetime, timezone
import pytest
from wxcli.migration.models import CanonicalDeviceSettingsTemplate, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.execute.planner import expand_to_operations

@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()

def _prov():
    return Provenance(source_system="cucm", source_id="pk-test", source_name="test",
                      extracted_at=datetime.now(timezone.utc))

def test_template_expands_to_location_settings_op(store):
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", location_canonical_id="location:HQ",
        settings={"bluetooth": {"enabled": True}},
        per_device_overrides=[], phones_using=10,
    )
    store.upsert_object(tmpl)
    ops = expand_to_operations(store)
    loc_ops = [op for op in ops if op.op_type == "apply_location_settings"]
    assert len(loc_ops) == 1
    assert loc_ops[0].resource_type == "device_settings_template"
    assert loc_ops[0].tier == 1

def test_template_with_overrides_expands(store):
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", location_canonical_id="location:HQ",
        settings={"bluetooth": {"enabled": True}},
        per_device_overrides=[
            {"device_canonical_id": "device:SEP001", "settings": {"bluetooth": {"enabled": False}}},
            {"device_canonical_id": "device:SEP002", "settings": {"bluetooth": {"enabled": False}}},
        ],
        phones_using=10,
    )
    store.upsert_object(tmpl)
    ops = expand_to_operations(store)
    loc_ops = [op for op in ops if op.op_type == "apply_location_settings"]
    dev_ops = [op for op in ops if op.op_type == "apply_device_override"]
    assert len(loc_ops) == 1
    assert len(dev_ops) == 2
    assert all(op.tier == 5 for op in dev_ops)

def test_empty_settings_no_ops(store):
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", location_canonical_id="location:HQ",
        settings={}, per_device_overrides=[], phones_using=0,
    )
    store.upsert_object(tmpl)
    ops = expand_to_operations(store)
    assert len(ops) == 0

def test_zero_phones_using_no_ops(store):
    """phones_using == 0 means the template is unused — skip even if settings exist."""
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", location_canonical_id="location:HQ",
        settings={"bluetooth": {"enabled": True}},
        per_device_overrides=[], phones_using=0,
    )
    store.upsert_object(tmpl)
    ops = expand_to_operations(store)
    assert len(ops) == 0

def test_override_depends_on_location_settings(store):
    """Per-device override ops depend on apply_location_settings."""
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", location_canonical_id="location:HQ",
        settings={"bluetooth": {"enabled": True}},
        per_device_overrides=[
            {"device_canonical_id": "device:SEP001", "settings": {"bluetooth": {"enabled": False}}},
        ],
        phones_using=5,
    )
    store.upsert_object(tmpl)
    ops = expand_to_operations(store)
    dev_op = next(op for op in ops if op.op_type == "apply_device_override")
    expected_dep = "device_settings_template:9800:location:HQ:apply_location_settings"
    assert expected_dep in dev_op.depends_on
