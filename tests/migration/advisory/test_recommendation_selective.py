"""Tests for selective call handling recommendation rule extension."""
from __future__ import annotations

from wxcli.migration.advisory.recommendation_rules import (
    recommend_feature_approximation,
)


class TestRecommendSelective:
    def test_selective_multi_partition_recommends_accept(self):
        context = {
            "selective_call_handling_pattern": "multi_partition_dn",
            "dn_number": "1001",
            "recommended_webex_feature": "Selective Forward",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        option_id, reasoning = result
        assert option_id == "accept"
        assert "selective forward" in reasoning.lower()

    def test_selective_low_membership_recommends_accept(self):
        context = {
            "selective_call_handling_pattern": "low_membership_partition",
            "recommended_webex_feature": "Selective Accept",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        assert result[0] == "accept"
        assert "selective accept" in result[1].lower()

    def test_selective_naming_only_recommends_accept_low_confidence(self):
        context = {
            "selective_call_handling_pattern": "naming_convention",
            "confidence": "LOW",
            "recommended_webex_feature": "Priority Alert",
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        assert result[0] == "accept"
        assert "priority alert" in result[1].lower()
        assert "user-only" in result[1].lower() or "weak" in result[1].lower()

    def test_non_selective_feature_approx_not_affected(self):
        """Existing behaviour for non-selective contexts must not change."""
        context = {
            "classification": "EXTENSION_MOBILITY",
            "line_count": 1,
            "speed_dial_count": 0,
            "blf_count": 0,
        }
        result = recommend_feature_approximation(context, [])
        assert result is not None
        # EM still recommends accept (existing behaviour)
        assert result[0] == "accept"
