"""Tests for ButtonTemplateMapper — CUCM button features → Webex LineKeyType."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    DecisionType,
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.mappers.button_template_mapper import (
    ButtonTemplateMapper,
    CUCM_BUTTON_TO_WEBEX,
    _MODEL_LINE_KEY_COUNTS,
    _parse_model_from_base_template,
)


def _prov(name="test"):
    return Provenance(
        source_system="cucm", source_id=f"uuid-{name}", source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_button_template(
    name: str = "Standard 8845",
    base: str = "Standard 8845",
    buttons: list[dict] | None = None,
) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"button_template:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "name": name,
            "base_template": base,
            "buttons": buttons or [],
        },
    )


def _make_phone(name: str, template_name: str) -> MigrationObject:
    return MigrationObject(
        canonical_id=f"phone:{name}",
        provenance=_prov(name),
        status=MigrationStatus.NORMALIZED,
        pre_migration_state={
            "cucm_phone_template": template_name,
            "cucm_device_pool": None,
            "cucm_owner_user": None,
        },
    )


def _setup(template, phones=None):
    store = MigrationStore(":memory:")
    store.upsert_object(template)
    for p in (phones or []):
        store.upsert_object(p)
        store.add_cross_ref(p.canonical_id, template.canonical_id, "phone_uses_button_template")
    return store


class TestButtonFeatureMapping:
    def test_line_maps_to_primary_line(self):
        tmpl = _make_button_template(buttons=[{"index": 1, "feature": "Line"}])
        store = _setup(tmpl)
        result = ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj is not None
        keys = obj["line_keys"]
        assert len(keys) == 1
        assert keys[0]["key_type"] == "PRIMARY_LINE"

    def test_speed_dial_maps(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Speed Dial"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["line_keys"][1]["key_type"] == "SPEED_DIAL"

    def test_blf_maps_to_monitor(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Busy Lamp Field"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["line_keys"][1]["key_type"] == "MONITOR"

    def test_call_park_maps(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Call Park"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["line_keys"][1]["key_type"] == "CALL_PARK_EXTENSION"

    def test_abbreviated_dial_maps_to_speed_dial(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Abbreviated Dial"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["line_keys"][1]["key_type"] == "SPEED_DIAL"

    def test_none_unassigned_map_to_open(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "None"},
            {"index": 3, "feature": "Unassigned"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["line_keys"][1]["key_type"] == "OPEN"
        assert obj["line_keys"][2]["key_type"] == "OPEN"


class TestUnmappedButtons:
    def test_service_url_is_unmapped(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Service URL"},
        ])
        phone = _make_phone("SEP001122334455", "Standard 8845")
        store = _setup(tmpl, [phone])
        result = ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert len(obj["unmapped_buttons"]) == 1
        assert obj["unmapped_buttons"][0]["feature"] == "Service URL"

    def test_privacy_intercom_unmapped(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Privacy"},
            {"index": 3, "feature": "Intercom"},
        ])
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert len(obj["unmapped_buttons"]) == 2


class TestKemBoundary:
    def test_buttons_beyond_max_go_to_kem(self):
        # 7821 has 2 line keys — buttons 3+ are KEM
        buttons = [
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Line"},
            {"index": 3, "feature": "Speed Dial"},
            {"index": 4, "feature": "Busy Lamp Field"},
        ]
        tmpl = _make_button_template(name="Standard 7821", base="Standard 7821", buttons=buttons)
        store = _setup(tmpl)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 7821")
        assert len(obj["line_keys"]) == 2
        assert len(obj["kem_keys"]) == 2
        assert obj["kem_keys"][0]["key_type"] == "SPEED_DIAL"


class TestDecisionUnmappable:
    def test_generates_button_unmappable_decision(self):
        tmpl = _make_button_template(buttons=[
            {"index": 1, "feature": "Line"},
            {"index": 2, "feature": "Service URL"},
        ])
        phone = _make_phone("SEP001122334455", "Standard 8845")
        store = _setup(tmpl, [phone])
        result = ButtonTemplateMapper().map(store)
        assert len(result.decisions) == 1
        assert result.decisions[0].type == DecisionType.BUTTON_UNMAPPABLE


class TestUsageCount:
    def test_phones_using_populated(self):
        tmpl = _make_button_template(buttons=[{"index": 1, "feature": "Line"}])
        phones = [
            _make_phone("SEP111111111111", "Standard 8845"),
            _make_phone("SEP222222222222", "Standard 8845"),
        ]
        store = _setup(tmpl, phones)
        ButtonTemplateMapper().map(store)
        obj = store.get_object("line_key_template:Standard 8845")
        assert obj["phones_using"] == 2


class TestParseModel:
    def test_standard_8845(self):
        assert _parse_model_from_base_template("Standard 8845") == "8845"

    def test_universal(self):
        assert _parse_model_from_base_template("Universal Phone Template") is None

    def test_cisco_ip_phone(self):
        assert _parse_model_from_base_template("Standard Cisco 9841") == "9841"
