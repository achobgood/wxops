"""Tests for Tier2-Phase2 appendix sections: button templates, device layouts, softkeys."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalDeviceLayout,
    CanonicalLineKeyTemplate,
    CanonicalSoftkeyConfig,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.report.appendix import (
    _button_template_group,
    _device_layout_group,
    _softkey_group,
    generate_appendix,
)
from wxcli.migration.store import MigrationStore


def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=name,
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _make_store() -> tuple[MigrationStore, str]:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return MigrationStore(tmp.name), tmp.name


class TestButtonTemplateGroup:
    """Spec §7.2: Button template inventory appendix section."""

    def test_renders_with_data(self):
        store, path = _make_store()
        try:
            store.upsert_object(CanonicalLineKeyTemplate(
                canonical_id="line_key_template:Standard 8845",
                provenance=_prov("Standard 8845"),
                status=MigrationStatus.ANALYZED,
                name="Standard 8845",
                cucm_template_name="Standard 8845",
                device_model="DMS Cisco 8845",
                line_keys=[
                    {"index": 1, "key_type": "PRIMARY_LINE"},
                    {"index": 2, "key_type": "SPEED_DIAL"},
                    {"index": 3, "key_type": "MONITOR"},
                ],
                unmapped_buttons=[
                    {"index": 4, "feature": "Service URL"},
                ],
                phones_using=15,
            ))

            html = _button_template_group(store)
            assert html != ""
            assert "<details" in html
            assert "<summary>" in html
            assert "Standard 8845" in html
            assert "15" in html  # phones_using count
            assert "PRIMARY_LINE" in html or "Line" in html
            assert "SPEED_DIAL" in html or "Speed Dial" in html
            assert "Service URL" in html or "unmapped" in html.lower()
        finally:
            store.close()

    def test_empty_store_returns_empty(self):
        store, path = _make_store()
        try:
            html = _button_template_group(store)
            assert html == ""
        finally:
            store.close()


class TestDeviceLayoutGroup:
    """Spec §7.3: Device layout summary appendix section."""

    def test_renders_with_data(self):
        store, path = _make_store()
        try:
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id="device_layout:SEP001122334455",
                provenance=_prov("SEP001122334455"),
                status=MigrationStatus.ANALYZED,
                device_canonical_id="device:SEP001122334455",
                template_canonical_id="line_key_template:Standard 8845",
                resolved_line_keys=[
                    {"index": 1, "key_type": "PRIMARY_LINE"},
                    {"index": 2, "key_type": "SHARED_LINE"},
                    {"index": 3, "key_type": "MONITOR", "target_canonical_id": "user:jdoe"},
                ],
                speed_dials=[
                    {"index": 4, "label": "Reception", "number": "1000"},
                ],
                resolved_kem_keys=[
                    {"index": 1, "key_type": "SPEED_DIAL"},
                ],
            ))

            html = _device_layout_group(store)
            assert html != ""
            assert "<details" in html
            assert "<summary>" in html
            # Should show stats about shared lines, speed dials, BLF, KEM
            assert "shared" in html.lower() or "SHARED" in html
            assert "speed" in html.lower() or "Speed" in html
        finally:
            store.close()

    def test_empty_store_returns_empty(self):
        store, path = _make_store()
        try:
            html = _device_layout_group(store)
            assert html == ""
        finally:
            store.close()


class TestSoftkeyGroup:
    """Spec §7.4: Softkey migration status appendix section."""

    def test_renders_with_data(self):
        store, path = _make_store()
        try:
            store.upsert_object(CanonicalSoftkeyConfig(
                canonical_id="softkey_config:Standard User",
                provenance=_prov("Standard User"),
                status=MigrationStatus.ANALYZED,
                cucm_template_name="Standard User",
                is_psk_target=True,
                psk_mappings=[
                    {"psk_slot": "PSK1", "keyword": "park"},
                    {"psk_slot": "PSK2", "keyword": "pickup"},
                ],
                unmapped_softkeys=[
                    {"cucm_name": "iDivert", "call_state": "Connected"},
                ],
                phones_using=8,
            ))

            html = _softkey_group(store)
            assert html != ""
            assert "<details" in html
            assert "<summary>" in html
            assert "Standard User" in html
            assert "8" in html  # phones_using
            assert "PSK" in html or "psk" in html.lower()
            assert "iDivert" in html or "unmapped" in html.lower()
        finally:
            store.close()

    def test_classic_mpp_not_psk(self):
        store, path = _make_store()
        try:
            store.upsert_object(CanonicalSoftkeyConfig(
                canonical_id="softkey_config:Classic Template",
                provenance=_prov("Classic Template"),
                status=MigrationStatus.ANALYZED,
                cucm_template_name="Classic Template",
                is_psk_target=False,
                phones_using=20,
            ))

            html = _softkey_group(store)
            assert html != ""
            assert "Classic Template" in html
            assert "20" in html
        finally:
            store.close()

    def test_empty_store_returns_empty(self):
        store, path = _make_store()
        try:
            html = _softkey_group(store)
            assert html == ""
        finally:
            store.close()


class TestAppendixRegistration:
    """Verify new groups are wired into generate_appendix."""

    def test_button_template_group_in_appendix(self):
        store, path = _make_store()
        try:
            store.upsert_object(CanonicalLineKeyTemplate(
                canonical_id="line_key_template:Test",
                provenance=_prov("Test"),
                status=MigrationStatus.ANALYZED,
                name="Test",
                phones_using=5,
                line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
            ))
            html = generate_appendix(store)
            assert "button-templates" in html or "Button Template" in html
        finally:
            store.close()
