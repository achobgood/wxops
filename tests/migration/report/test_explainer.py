"""Tests for the explainer module — decision type templates and generic handler."""

import pytest


class TestExplainDecision:
    """Core explain_decision() dispatch and fallback behavior."""

    def test_known_type_returns_template_dict(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision(
            "EXTENSION_CONFLICT", "HIGH", "Extension 1001 is duplicated", {"dn": "1001", "count": 3}
        )
        assert "title" in result
        assert "explanation" in result
        assert "reassurance" in result

    def test_unknown_type_falls_back_to_generic(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision(
            "UNKNOWN_MYSTERY_TYPE", "LOW", "Something happened", {}
        )
        assert result["title"] == "Unknown Mystery Type"

    def test_none_summary_does_not_crash(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "LOW", None, {})
        assert result["title"]

    def test_none_context_does_not_crash(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "LOW", "Some summary", None)
        assert result["title"]


class TestReassuranceForSeverity:
    """Reassurance text varies by severity."""

    def test_critical_reassurance(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "CRITICAL", "", {})
        assert "must be resolved" in result["reassurance"]

    def test_high_reassurance(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "HIGH", "", {})
        assert "requires planning" in result["reassurance"]

    def test_low_reassurance(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "LOW", "", {})
        assert "configuration choice" in result["reassurance"]

    def test_medium_reassurance(self):
        from wxcli.migration.report.explainer import explain_decision

        result = explain_decision("EXTENSION_CONFLICT", "MEDIUM", "", {})
        assert "configuration choice" in result["reassurance"]


class TestAllTemplatesRegistered:
    """Smoke test — all expected decision types have templates."""

    EXPECTED_TYPES = [
        "EXTENSION_CONFLICT",
        "DN_AMBIGUOUS",
        "DEVICE_INCOMPATIBLE",
        "DEVICE_FIRMWARE_CONVERTIBLE",
        "SHARED_LINE_COMPLEX",
        "CSS_ROUTING_MISMATCH",
        "CALLING_PERMISSION_MISMATCH",
        "LOCATION_AMBIGUOUS",
        "DUPLICATE_USER",
        "VOICEMAIL_INCOMPATIBLE",
        "WORKSPACE_LICENSE_TIER",
        "WORKSPACE_TYPE_UNCERTAIN",
        "HOTDESK_DN_CONFLICT",
        "FEATURE_APPROXIMATION",
        "MISSING_DATA",
        "NUMBER_CONFLICT",
        "ARCHITECTURE_ADVISORY",
        "AUDIO_ASSET_MANUAL",
    ]

    def test_all_expected_types_registered(self):
        from wxcli.migration.report.explainer import _TEMPLATES

        for decision_type in self.EXPECTED_TYPES:
            assert decision_type in _TEMPLATES, f"{decision_type} not in _TEMPLATES"


class TestDecisionTypeDisplayNames:
    """DECISION_TYPE_DISPLAY_NAMES covers all known types."""

    def test_audio_asset_manual_display_name(self):
        from wxcli.migration.report.explainer import DECISION_TYPE_DISPLAY_NAMES

        assert "AUDIO_ASSET_MANUAL" in DECISION_TYPE_DISPLAY_NAMES
        assert DECISION_TYPE_DISPLAY_NAMES["AUDIO_ASSET_MANUAL"] == "Audio Asset Migration"


class TestExplainAudioAssetManual:
    def test_with_source_name(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "AUDIO_ASSET_MANUAL", "MEDIUM",
            "Custom MoH source",
            {"source_name": "Corporate_Hold", "source_type": "MoH"},
        )
        assert "Corporate_Hold" in result["title"]
        assert "WAV" in result["explanation"]
        assert "8 MB" in result["explanation"]
        assert "Control Hub" in result["explanation"]

    def test_without_source_name(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "AUDIO_ASSET_MANUAL", "HIGH",
            "Audio asset migration needed",
            {},
        )
        assert "Audio asset" in result["title"]
        assert "downloaded from CUCM" in result["explanation"]
        assert result["reassurance"]  # not empty

    def test_registered_in_templates(self):
        from wxcli.migration.report.explainer import explain_decision
        result = explain_decision(
            "AUDIO_ASSET_MANUAL", "LOW", "", {},
        )
        # Should NOT fall through to generic handler
        # The generic handler does .replace("_", " ").title() which would produce "Audio Asset Manual"
        assert result["title"] != "Audio Asset Manual"
