"""Tests for Tier2-Phase2 recommendation rules."""
from wxcli.migration.advisory.recommendation_rules import (
    RECOMMENDATION_DISPATCH,
    recommend_button_unmappable,
)


class TestRecommendButtonUnmappable:
    """Spec §6.1: BUTTON_UNMAPPABLE always returns accept_loss."""

    def test_always_returns_accept_loss(self):
        result = recommend_button_unmappable(
            {"template_name": "Standard 8845", "unmapped_features": ["Service URL", "Privacy"]},
            [],
        )
        assert result is not None
        option_id, reasoning = result
        assert option_id == "accept_loss"
        assert "no Webex equivalent" in reasoning.lower() or "no webex" in reasoning.lower()

    def test_reasoning_mentions_cucm_specific(self):
        result = recommend_button_unmappable(
            {"template_name": "Custom-HQ", "unmapped_features": ["Intercom"]},
            [],
        )
        assert result is not None
        option_id, reasoning = result
        assert option_id == "accept_loss"
        assert "cucm" in reasoning.lower() or "webex" in reasoning.lower()

    def test_empty_context(self):
        result = recommend_button_unmappable({}, [])
        assert result is not None
        assert result[0] == "accept_loss"

    def test_registered_in_dispatch(self):
        assert "BUTTON_UNMAPPABLE" in RECOMMENDATION_DISPATCH
        assert RECOMMENDATION_DISPATCH["BUTTON_UNMAPPABLE"] is recommend_button_unmappable
