"""Tests for Tier2-Phase2 canonical types."""
from wxcli.migration.models import (
    CanonicalDeviceLayout,
    CanonicalLineKeyTemplate,
    CanonicalSoftkeyConfig,
    DecisionType,
    MigrationStatus,
    Provenance,
)
from datetime import datetime, timezone


def _prov():
    return Provenance(
        source_system="cucm", source_id="test", source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


class TestCanonicalLineKeyTemplate:
    def test_create_with_defaults(self):
        obj = CanonicalLineKeyTemplate(
            canonical_id="line_key_template:Standard 8845",
            provenance=_prov(),
        )
        assert obj.name is None
        assert obj.line_keys == []
        assert obj.kem_keys == []
        assert obj.unmapped_buttons == []
        assert obj.phones_using == 0
        assert obj.kem_module_type is None

    def test_create_with_values(self):
        obj = CanonicalLineKeyTemplate(
            canonical_id="line_key_template:Standard 8845",
            provenance=_prov(),
            name="Standard 8845",
            cucm_template_name="Standard 8845",
            device_model="DMS Cisco 8845",
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
            phones_using=12,
        )
        assert obj.name == "Standard 8845"
        assert len(obj.line_keys) == 1
        assert obj.phones_using == 12


class TestCanonicalDeviceLayout:
    def test_create_with_defaults(self):
        obj = CanonicalDeviceLayout(
            canonical_id="device_layout:SEP001122334455",
            provenance=_prov(),
        )
        assert obj.device_canonical_id is None
        assert obj.template_canonical_id is None
        assert obj.line_members == []
        assert obj.resolved_line_keys == []
        assert obj.resolved_kem_keys == []
        assert obj.speed_dials == []
        assert obj.unmapped_buttons == []


class TestCanonicalSoftkeyConfig:
    def test_create_with_defaults(self):
        obj = CanonicalSoftkeyConfig(
            canonical_id="softkey_config:Standard User",
            provenance=_prov(),
        )
        assert obj.cucm_template_name is None
        assert obj.is_psk_target is False
        assert obj.psk_mappings == []
        assert obj.state_key_lists == {}
        assert obj.unmapped_softkeys == []
        assert obj.phones_using == 0


class TestDecisionTypeButtonUnmappable:
    def test_enum_value_exists(self):
        assert DecisionType.BUTTON_UNMAPPABLE == "BUTTON_UNMAPPABLE"
        assert DecisionType.BUTTON_UNMAPPABLE.value == "BUTTON_UNMAPPABLE"
