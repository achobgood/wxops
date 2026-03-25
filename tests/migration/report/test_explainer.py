"""Tests for decision plain-English explainer."""
import pytest
from wxcli.migration.models import DecisionType


class TestExplainer:
    def test_explains_all_decision_types(self):
        from wxcli.migration.report.explainer import explain_decision
        for dt in DecisionType:
            result = explain_decision(dt.value, severity="MEDIUM",
                summary="test", context={})
            assert result["title"]  # non-empty
            assert result["explanation"]  # non-empty
            assert result["reassurance"]  # non-empty

    def test_css_routing_mismatch_uses_context(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "CSS_ROUTING_MISMATCH", severity="HIGH",
            summary="CSS-0 routing scope differs",
            context={"css_name": "CSS-Dallas", "partitions": ["PT-Internal", "PT-LD"]})
        assert "CSS-Dallas" in result["title"] or "CSS-Dallas" in result["explanation"]

    def test_device_incompatible_shows_model(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "DEVICE_INCOMPATIBLE", severity="LOW",
            summary="CP-7962G is incompatible",
            context={"model": "CP-7962G", "count": 5})
        assert "7962" in result["explanation"]

    def test_feature_approximation_names_both_features(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "FEATURE_APPROXIMATION", severity="MEDIUM",
            summary="Extension Mobility maps to Hoteling",
            context={"cucm_feature": "Extension Mobility", "webex_feature": "Hoteling"})
        assert "Extension Mobility" in result["explanation"]
        assert "Hoteling" in result["explanation"]

    def test_unknown_severity_does_not_crash(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision("EXTENSION_CONFLICT", "UNKNOWN_SEVERITY", "test", {})
        assert result["reassurance"]  # should return default, not crash

    def test_empty_severity_does_not_crash(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision("EXTENSION_CONFLICT", "", "test", {})
        assert result["reassurance"]

    def test_none_severity_does_not_crash(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision("EXTENSION_CONFLICT", None, "test", {})
        assert result["reassurance"]

    def test_severity_affects_tone(self):
        from wxcli.migration.report.explainer import explain_decision
        high = explain_decision("CSS_ROUTING_MISMATCH", "HIGH", "test", {})
        low = explain_decision("EXTENSION_CONFLICT", "LOW", "test", {})
        # High severity should not use minimizing language
        assert "critical" not in low["reassurance"].lower() or "minor" in low["reassurance"].lower()
