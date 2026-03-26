"""Tests for migration complexity score algorithm."""

import pytest


class TestComplexityScore:
    """Score should be 0-100 with 8 weighted factors."""

    def test_score_returns_int_in_range(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        assert 0 <= result.score <= 100

    def test_score_has_seven_factors(self, populated_store):
        from wxcli.migration.report.score import compute_complexity_score

        result = compute_complexity_score(populated_store)
        assert len(result.factors) == 8

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
        """With 40/45 native MPP, device factor should be low."""
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
