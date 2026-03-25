"""Tests for advisory foundation: Decision model fields, store, and decision_to_store_dict."""
import json
import os
import tempfile

import pytest

from wxcli.migration.models import Decision, DecisionOption, DecisionType


class TestDecisionRecommendationFields:
    def test_default_none(self):
        d = Decision(
            decision_id="D0001", type=DecisionType.FEATURE_APPROXIMATION,
            severity="HIGH", summary="test", context={},
            options=[DecisionOption(id="a", label="A", impact="x")],
            fingerprint="abc123", run_id="run1",
        )
        assert d.recommendation is None
        assert d.recommendation_reasoning is None

    def test_set_values(self):
        d = Decision(
            decision_id="D0001", type=DecisionType.FEATURE_APPROXIMATION,
            severity="HIGH", summary="test", context={},
            options=[DecisionOption(id="a", label="A", impact="x")],
            fingerprint="abc123", run_id="run1",
            recommendation="a",
            recommendation_reasoning="because reasons",
        )
        assert d.recommendation == "a"
        assert d.recommendation_reasoning == "because reasons"


class TestArchitectureAdvisoryEnum:
    def test_enum_exists(self):
        assert DecisionType.ARCHITECTURE_ADVISORY == "ARCHITECTURE_ADVISORY"


from wxcli.migration.transform.mappers.base import decision_to_store_dict


class TestDecisionToStoreDictRecommendation:
    def _make_decision(self, **kwargs):
        defaults = dict(
            decision_id="D0001", type=DecisionType.FEATURE_APPROXIMATION,
            severity="HIGH", summary="test", context={},
            options=[DecisionOption(id="a", label="A", impact="x")],
            fingerprint="abc123", run_id="run1",
        )
        defaults.update(kwargs)
        return Decision(**defaults)

    def test_includes_recommendation(self):
        d = self._make_decision(recommendation="a", recommendation_reasoning="reason")
        result = decision_to_store_dict(d)
        assert result["recommendation"] == "a"
        assert result["recommendation_reasoning"] == "reason"

    def test_none_when_not_set(self):
        d = self._make_decision()
        result = decision_to_store_dict(d)
        assert result["recommendation"] is None
        assert result["recommendation_reasoning"] is None


from wxcli.migration.store import MigrationStore


class TestStoreRecommendation:
    def _make_store(self, tmp_path):
        return MigrationStore(os.path.join(str(tmp_path), "test.db"))

    def test_save_and_get_with_recommendation(self, tmp_path):
        store = self._make_store(tmp_path)
        store.save_decision({
            "decision_id": "D0001", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "test", "context": {},
            "options": [{"id": "a", "label": "A", "impact": "x"}],
            "fingerprint": "fp001", "run_id": "run1",
            "recommendation": "a", "recommendation_reasoning": "reason",
        })
        d = store.get_decision("D0001")
        assert d["recommendation"] == "a"
        assert d["recommendation_reasoning"] == "reason"

    def test_save_without_recommendation(self, tmp_path):
        store = self._make_store(tmp_path)
        store.save_decision({
            "decision_id": "D0001", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "test", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run1",
        })
        d = store.get_decision("D0001")
        assert d.get("recommendation") is None

    def test_update_recommendation(self, tmp_path):
        store = self._make_store(tmp_path)
        store.save_decision({
            "decision_id": "D0001", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "test", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run1",
        })
        store.update_recommendation("D0001", "a", "new reasoning")
        d = store.get_decision("D0001")
        assert d["recommendation"] == "a"
        assert d["recommendation_reasoning"] == "new reasoning"

    def test_merge_updates_recommendation_on_kept(self, tmp_path):
        """Resolved decision: merge updates recommendation text, preserves chosen_option."""
        store = self._make_store(tmp_path)
        store.save_decision({
            "decision_id": "D0001", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "v1", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run1",
            "chosen_option": "a", "resolved_by": "user", "resolved_at": "2026-01-01",
            "recommendation": "a", "recommendation_reasoning": "v1 reasoning",
        })
        store.merge_decisions([{
            "decision_id": "D9999", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "v2", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run2",
            "recommendation": "a", "recommendation_reasoning": "v2 reasoning",
        }])
        d = store.get_decision("D0001")
        assert d["chosen_option"] == "a"  # resolution preserved
        assert d["recommendation_reasoning"] == "v2 reasoning"  # rec updated

    def test_merge_updates_recommendation_on_pending(self, tmp_path):
        """Pending decision: merge updates recommendation alongside other display fields."""
        store = self._make_store(tmp_path)
        store.save_decision({
            "decision_id": "D0001", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "v1", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run1",
            "recommendation": "a", "recommendation_reasoning": "v1",
        })
        store.merge_decisions([{
            "decision_id": "D9999", "type": "FEATURE_APPROXIMATION",
            "severity": "HIGH", "summary": "v2", "context": {},
            "options": [], "fingerprint": "fp001", "run_id": "run2",
            "recommendation": "b", "recommendation_reasoning": "v2",
        }])
        d = store.get_decision("D0001")
        assert d["recommendation"] == "b"
        assert d["recommendation_reasoning"] == "v2"
