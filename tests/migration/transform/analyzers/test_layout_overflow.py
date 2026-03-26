"""Tests for LayoutOverflowAnalyzer — detects button count overflow and KEM incompatibility.

From spec §5.1 and §10.7.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    CanonicalDevice,
    CanonicalDeviceLayout,
    DecisionType,
    DeviceCompatibilityTier,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.analyzers.layout_overflow import LayoutOverflowAnalyzer


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


class TestOverflowLineCountExceeded:
    """Spec §10.7: more buttons than device supports → FEATURE_APPROXIMATION decision."""

    def test_overflow_produces_decision(self):
        store, path = _make_store()
        try:
            # 8845 has 10 line keys max. Create a layout with 12 resolved keys.
            store.upsert_object(CanonicalDevice(
                canonical_id="device:SEP001122334455",
                provenance=_prov("SEP001122334455"),
                status=MigrationStatus.ANALYZED,
                model="CP-8845",
                mac="001122334455",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            ))
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id="device_layout:SEP001122334455",
                provenance=_prov("SEP001122334455"),
                status=MigrationStatus.ANALYZED,
                device_canonical_id="device:SEP001122334455",
                template_canonical_id="line_key_template:Custom 8845",
                resolved_line_keys=[
                    {"index": i, "key_type": "PRIMARY_LINE"} for i in range(1, 13)
                ],
            ))

            analyzer = LayoutOverflowAnalyzer()
            decisions = analyzer.analyze(store)

            assert len(decisions) >= 1
            overflow_decisions = [
                d for d in decisions
                if d.type == DecisionType.FEATURE_APPROXIMATION
                and ("overflow" in d.summary.lower() or "exceed" in d.summary.lower())
            ]
            assert len(overflow_decisions) >= 1
            d = overflow_decisions[0]
            assert d.severity == "MEDIUM"
            assert len(d.options) == 3
            option_ids = [o.id for o in d.options]
            assert "accept" in option_ids
            assert "manual" in option_ids
            assert "skip" in option_ids
        finally:
            store.close()


class TestOverflowKEMNotSupported:
    """Spec §10.7: KEM buttons on non-KEM device → FEATURE_APPROXIMATION decision."""

    def test_kem_on_non_kem_device_produces_decision(self):
        store, path = _make_store()
        try:
            # 7841 does NOT support KEM. Create layout with KEM keys.
            store.upsert_object(CanonicalDevice(
                canonical_id="device:SEP112233445566",
                provenance=_prov("SEP112233445566"),
                status=MigrationStatus.ANALYZED,
                model="CP-7841",
                mac="112233445566",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            ))
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id="device_layout:SEP112233445566",
                provenance=_prov("SEP112233445566"),
                status=MigrationStatus.ANALYZED,
                device_canonical_id="device:SEP112233445566",
                template_canonical_id="line_key_template:Custom KEM",
                resolved_line_keys=[
                    {"index": 1, "key_type": "PRIMARY_LINE"},
                ],
                resolved_kem_keys=[
                    {"index": 1, "key_type": "SPEED_DIAL", "label": "Reception"},
                ],
            ))

            analyzer = LayoutOverflowAnalyzer()
            decisions = analyzer.analyze(store)

            kem_decisions = [
                d for d in decisions
                if d.type == DecisionType.FEATURE_APPROXIMATION
                and "kem" in d.summary.lower()
            ]
            assert len(kem_decisions) >= 1
            d = kem_decisions[0]
            assert d.severity == "MEDIUM"
            option_ids = [o.id for o in d.options]
            assert "accept_loss" in option_ids
            assert "manual" in option_ids
        finally:
            store.close()


class TestNoOverflow:
    """Spec §10.7: button count within limits → no decision."""

    def test_within_limits_no_decision(self):
        store, path = _make_store()
        try:
            # 8845 has 10 line keys. Layout has only 4 → no overflow.
            store.upsert_object(CanonicalDevice(
                canonical_id="device:SEP223344556677",
                provenance=_prov("SEP223344556677"),
                status=MigrationStatus.ANALYZED,
                model="CP-8845",
                mac="223344556677",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            ))
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id="device_layout:SEP223344556677",
                provenance=_prov("SEP223344556677"),
                status=MigrationStatus.ANALYZED,
                device_canonical_id="device:SEP223344556677",
                template_canonical_id="line_key_template:Standard 8845",
                resolved_line_keys=[
                    {"index": i, "key_type": "PRIMARY_LINE"} for i in range(1, 5)
                ],
                resolved_kem_keys=[],
            ))

            analyzer = LayoutOverflowAnalyzer()
            decisions = analyzer.analyze(store)

            assert len(decisions) == 0
        finally:
            store.close()

    def test_kem_on_supported_device_no_decision(self):
        store, path = _make_store()
        try:
            # 8845 supports KEM. Layout with KEM keys → no KEM decision.
            store.upsert_object(CanonicalDevice(
                canonical_id="device:SEP334455667788",
                provenance=_prov("SEP334455667788"),
                status=MigrationStatus.ANALYZED,
                model="CP-8845",
                mac="334455667788",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
            ))
            store.upsert_object(CanonicalDeviceLayout(
                canonical_id="device_layout:SEP334455667788",
                provenance=_prov("SEP334455667788"),
                status=MigrationStatus.ANALYZED,
                device_canonical_id="device:SEP334455667788",
                template_canonical_id="line_key_template:Standard 8845",
                resolved_line_keys=[
                    {"index": 1, "key_type": "PRIMARY_LINE"},
                ],
                resolved_kem_keys=[
                    {"index": 1, "key_type": "SPEED_DIAL", "label": "Lobby"},
                ],
            ))

            analyzer = LayoutOverflowAnalyzer()
            decisions = analyzer.analyze(store)

            # Should be zero — 8845 supports KEM and 1 key < 10 max
            assert len(decisions) == 0
        finally:
            store.close()
