"""Tests for migration complexity score algorithm."""

import pytest


class TestComplexityScore:
    """Score should be 0-100 with 9 weighted factors."""

    def test_score_returns_int_in_range(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        assert 0 <= result.score <= 100

    def test_score_has_nine_factors(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        assert len(result.factors) == 9

    def test_score_factors_have_required_fields(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        for factor in result.factors:
            assert "name" in factor
            assert "weight" in factor
            assert "raw_score" in factor  # 0-100 before weighting
            assert "weighted_score" in factor  # raw * weight
            assert "detail" in factor  # human-readable explanation

    def test_factor_weights_sum_to_100(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        total_weight = sum(f["weight"] for f in result.factors)
        assert total_weight == 100

    def test_score_label_straightforward(self, populated_store):
        """Fixture has moderate data — should score green or low amber."""
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        assert result.label in ("Straightforward", "Moderate")
        assert result.color in ("#2E7D32", "#F57C00")

    def test_empty_store_scores_zero(self, tmp_path):
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.score import compute_complexity_score

        store = MigrationStore(tmp_path / "empty.db")
        result = compute_complexity_score(store)
        assert result.score == 0
        assert result.label == "Straightforward"

    def test_device_factor_all_native(self, populated_store):
        """With 37/45 native MPP + 3 DECT, device factor should be low."""
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        device_factor = next(f for f in result.factors if f["name"] == "Device Compatibility")
        assert device_factor["raw_score"] < 30  # mostly native

    def test_decision_factor_scales_with_count(self, populated_store):
        """5 decisions / 50+ objects = low density."""
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        decision_factor = next(f for f in result.factors if f["name"] == "Decision Density")
        assert decision_factor["raw_score"] < 40

    def test_dect_not_counted_as_incompatible(self, tmp_path):
        """DECT devices should NOT inflate the incompatible device count."""
        from wxcli.migration.store import MigrationStore
        from wxcli.migration.report.score import compute_complexity_score
        from wxcli.migration.models import (
            CanonicalDevice, DeviceCompatibilityTier, MigrationStatus, Provenance,
        )
        from datetime import datetime, timezone

        store = MigrationStore(tmp_path / "dect_score.db")
        prov = Provenance(
            source_system="cucm", source_id="t", source_name="t",
            extracted_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        )

        # 10 native MPP + 5 DECT + 2 incompatible
        for i in range(10):
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:native-{i}", provenance=prov,
                status=MigrationStatus.ANALYZED, model="Cisco 8845",
                compatibility_tier=DeviceCompatibilityTier.NATIVE_MPP,
                mac=f"AABB0000{i:04d}",
            ))
        for i in range(5):
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:dect-{i}", provenance=prov,
                status=MigrationStatus.ANALYZED, model="Cisco 6825",
                compatibility_tier=DeviceCompatibilityTier.DECT,
                mac=f"DECT0000{i:04d}",
            ))
        for i in range(2):
            store.upsert_object(CanonicalDevice(
                canonical_id=f"device:incompat-{i}", provenance=prov,
                status=MigrationStatus.ANALYZED, model="Cisco 7962",
                compatibility_tier=DeviceCompatibilityTier.INCOMPATIBLE,
                mac=f"DEAD0000{i:04d}",
            ))

        result = compute_complexity_score(store)
        device_factor = next(f for f in result.factors if f["name"] == "Device Compatibility")

        # 2 incompatible out of 17 total = (2*100)/17 ≈ 11
        # If DECT were counted as incompatible, it would be (7*100)/17 ≈ 41
        assert device_factor["raw_score"] < 20
        assert "dect" in device_factor["detail"].lower() or "DECT" in device_factor["detail"]


def test_factors_have_display_names(populated_store):
    """Each factor dict should include a display_name field."""
    from wxcli.migration.report.score import compute_complexity_score

    result = compute_complexity_score(populated_store)
    for factor in result.factors:
        assert "display_name" in factor, f"Factor {factor['name']} missing display_name"
    # Check specific mappings
    names = {f["name"]: f["display_name"] for f in result.factors}
    assert names["CSS Complexity"] == "Calling Restrictions"
    assert names["Feature Parity"] == "Feature Compatibility"
    assert names["Device Compatibility"] == "Device Readiness"
    assert names["Decision Density"] == "Outstanding Decisions"
    assert names["Scale"] == "Scale"
    assert names["Shared Line Complexity"] == "Shared Lines"
    assert names["Routing Complexity"] == "Routing"
    assert names["Phone Config Complexity"] == "Phone Configuration"
    assert names["Device Settings Complexity"] == "Device Settings"


def test_phone_config_factor_with_data(tmp_path):
    """Phone config factor should score >0 when templates and layouts exist."""
    from datetime import datetime, timezone
    from wxcli.migration.models import (
        CanonicalLineKeyTemplate, CanonicalDeviceLayout, MigrationStatus, Provenance,
    )
    from wxcli.migration.store import MigrationStore
    from wxcli.migration.report.score import compute_complexity_score

    store = MigrationStore(tmp_path / "phone_config.db")
    prov = Provenance(source_system="cucm", source_id="t", source_name="t",
                      extracted_at=datetime.now(timezone.utc))

    for i in range(5):
        store.upsert_object(CanonicalLineKeyTemplate(
            canonical_id=f"line_key_template:Template{i}",
            provenance=prov, status=MigrationStatus.ANALYZED,
            name=f"Template{i}", phones_using=10,
            line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
            unmapped_buttons=[{"index": 2, "feature": "Service URL"}],
        ))
    store.upsert_object(CanonicalDeviceLayout(
        canonical_id="device_layout:SEP111111111111",
        provenance=prov, status=MigrationStatus.ANALYZED,
        device_canonical_id="device:SEP111111111111",
        template_canonical_id="line_key_template:Template0",
        resolved_line_keys=[{"index": 1, "key_type": "PRIMARY_LINE"}],
        resolved_kem_keys=[{"index": 1, "key_type": "SPEED_DIAL"}],
    ))

    result = compute_complexity_score(store)
    phone_factor = next(f for f in result.factors if f["name"] == "Phone Config Complexity")
    assert phone_factor["raw_score"] > 0
    assert "button templates" in phone_factor["detail"]
    assert "KEM" in phone_factor["detail"]
    assert "unmapped" in phone_factor["detail"]
    store.close()
