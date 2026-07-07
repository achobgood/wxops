"""Test Device Settings Complexity score factor."""
from datetime import datetime, timezone
from wxcli.migration.models import CanonicalDeviceSettingsTemplate, MigrationStatus, Provenance
from wxcli.migration.store import MigrationStore
from wxcli.migration.report.score import compute_score, WEIGHTS, DISPLAY_NAMES


def _prov():
    return Provenance(source_system="cucm", source_id="pk", source_name="test",
                      extracted_at=datetime.now(timezone.utc))


def test_device_settings_factor_in_weights():
    assert "Device Settings Complexity" in WEIGHTS


def test_device_settings_factor_in_display_names():
    assert "Device Settings Complexity" in DISPLAY_NAMES


def test_no_templates_zero_score():
    store = MigrationStore(":memory:")
    result = compute_score(store)
    factor = next((f for f in result.factors if f["name"] == "Device Settings Complexity"), None)
    assert factor is not None
    assert factor["raw_score"] == 0


def test_templates_with_overrides_higher_score():
    store = MigrationStore(":memory:")
    tmpl = CanonicalDeviceSettingsTemplate(
        canonical_id="device_settings_template:9800:location:HQ",
        provenance=_prov(), status=MigrationStatus.ANALYZED,
        model_family="9800", settings={"bluetooth": {"enabled": True}},
        per_device_overrides=[{"device_canonical_id": f"device:SEP{i}"} for i in range(25)],
        phones_using=100,
        unmappable_settings=["idleUrl", "enableExtensionMobility"],
    )
    store.upsert_object(tmpl)
    result = compute_score(store)
    factor = next((f for f in result.factors if f["name"] == "Device Settings Complexity"), None)
    assert factor is not None
    assert factor["raw_score"] > 0
