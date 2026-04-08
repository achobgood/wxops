"""Tests for auto-resolution rules engine.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.transform.rules import apply_auto_rules


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_store() -> MigrationStore:
    return MigrationStore(":memory:")


def _seed_decision(
    store: MigrationStore,
    decision_id: str = "D0001",
    dec_type: str = "DEVICE_INCOMPATIBLE",
    severity: str = "HIGH",
    summary: str = "Test device incompatible",
    chosen_option: str | None = None,
    resolved_by: str | None = None,
) -> None:
    """Seed a decision directly into the store."""
    store.save_decision({
        "decision_id": decision_id,
        "type": dec_type,
        "severity": severity,
        "summary": summary,
        "context": {"test": True},
        "options": [
            {"id": "skip", "label": "Skip", "impact": "Not migrated"},
            {"id": "manual", "label": "Manual", "impact": "Manual config"},
            {"id": "convert", "label": "Convert", "impact": "Firmware conversion"},
        ],
        "chosen_option": chosen_option,
        "resolved_at": None,
        "resolved_by": resolved_by,
        "fingerprint": f"fp_{decision_id}",
        "run_id": store.current_run_id,
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApplyAutoRules:
    """Test apply_auto_rules()."""

    def test_no_rules_returns_zero(self) -> None:
        store = _make_store()
        _seed_decision(store, "D0001")
        count = apply_auto_rules(store, {})
        assert count == 0

    def test_empty_rules_list_returns_zero(self) -> None:
        store = _make_store()
        _seed_decision(store, "D0001")
        count = apply_auto_rules(store, {"auto_rules": []})
        assert count == 0

    def test_resolves_matching_decision(self) -> None:
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        dec = store.get_decision("D0001")
        assert dec is not None
        assert dec["chosen_option"] == "skip"
        assert dec["resolved_by"] == "auto_rule"
        assert dec["resolved_at"] is not None

    def test_does_not_resolve_non_matching_type(self) -> None:
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="MISSING_DATA")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 0
        dec = store.get_decision("D0001")
        assert dec["chosen_option"] is None

    def test_does_not_overwrite_resolved_decision(self) -> None:
        """Already-resolved decisions are not re-resolved."""
        store = _make_store()
        _seed_decision(
            store,
            "D0001",
            dec_type="DEVICE_INCOMPATIBLE",
            chosen_option="manual",
            resolved_by="user",
        )

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 0
        dec = store.get_decision("D0001")
        # Should keep the original resolution
        assert dec["chosen_option"] == "manual"
        assert dec["resolved_by"] == "user"

    def test_resolves_multiple_decisions(self) -> None:
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_FIRMWARE_CONVERTIBLE")
        _seed_decision(store, "D0003", dec_type="MISSING_DATA")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
                {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 2

        d1 = store.get_decision("D0001")
        assert d1["chosen_option"] == "skip"
        assert d1["resolved_by"] == "auto_rule"

        d2 = store.get_decision("D0002")
        assert d2["chosen_option"] == "convert"
        assert d2["resolved_by"] == "auto_rule"

        d3 = store.get_decision("D0003")
        assert d3["chosen_option"] is None  # Unmatched

    def test_skips_invalid_choice(self) -> None:
        """If the choice doesn't match any option ID, skip the decision."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "nonexistent_choice"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 0
        dec = store.get_decision("D0001")
        assert dec["chosen_option"] is None

    def test_multiple_same_type_decisions(self) -> None:
        """Multiple pending decisions of the same type all get resolved."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 2
        assert store.get_decision("D0001")["chosen_option"] == "skip"
        assert store.get_decision("D0002")["chosen_option"] == "skip"

    def test_rules_with_malformed_entries_ignored(self) -> None:
        """Rules missing type or choice are silently ignored."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE"},  # Missing choice
                {"choice": "skip"},  # Missing type
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},  # Valid
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1


class TestAutoRulesMatchField:
    """Investigation 3: Auto-rule ``match`` field support.

    Tests the extended match format from 03-conflict-detection-engine.md:
    - List values: model in list
    - _lte suffix: dn_length <= 4
    - _gte suffix: greater-than-or-equal
    - _contains suffix: substring match
    - Multiple fields: AND logic
    - Missing context key: rule skipped, no crash
    """

    def test_type_only_rule_still_works(self) -> None:
        """Existing behavior: type-only rules (no match) still resolve."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        dec = store.get_decision("D0001")
        assert dec["chosen_option"] == "skip"

    def test_match_with_list_values(self) -> None:
        """Match with list: context value must be IN the list."""
        store = _make_store()

        # Decision whose context has cucm_model = "7841"
        store.save_decision({
            "decision_id": "D0001",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Convertible device",
            "context": {"cucm_model": "7841", "canonical_id": "d:1"},
            "options": [
                {"id": "convert", "label": "Convert", "impact": "Convert"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_match_list_1",
            "run_id": store.current_run_id,
        })

        # Decision whose context has cucm_model = "9971" (NOT in list)
        store.save_decision({
            "decision_id": "D0002",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Convertible device 2",
            "context": {"cucm_model": "9971", "canonical_id": "d:2"},
            "options": [
                {"id": "convert", "label": "Convert", "impact": "Convert"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_match_list_2",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DEVICE_FIRMWARE_CONVERTIBLE",
                    "match": {"cucm_model": ["7841", "7861"]},
                    "choice": "convert",
                },
            ]
        }
        count = apply_auto_rules(store, config)

        # Only the 7841 device should be resolved
        assert count == 1
        assert store.get_decision("D0001")["chosen_option"] == "convert"
        assert store.get_decision("D0002")["chosen_option"] is None

    def test_match_with_lte_suffix(self) -> None:
        """Match with _lte: context value <= threshold."""
        store = _make_store()

        # DN with length 4 (should match dn_length_lte: 4)
        store.save_decision({
            "decision_id": "D0001",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "4-digit DN",
            "context": {"dn_length": 4, "dn": "1001"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_lte_1",
            "run_id": store.current_run_id,
        })

        # DN with length 7 (should NOT match)
        store.save_decision({
            "decision_id": "D0002",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "7-digit DN",
            "context": {"dn_length": 7, "dn": "5551234"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_lte_2",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DN_AMBIGUOUS",
                    "match": {"dn_length_lte": 4},
                    "choice": "extension_only",
                },
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        assert store.get_decision("D0001")["chosen_option"] == "extension_only"
        assert store.get_decision("D0002")["chosen_option"] is None

    def test_match_with_gte_suffix(self) -> None:
        """Match with _gte: context value >= threshold."""
        store = _make_store()

        store.save_decision({
            "decision_id": "D0001",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "10-digit DN",
            "context": {"dn_length": 10, "dn": "5551234567"},
            "options": [
                {"id": "e164", "label": "E.164", "impact": "National"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_gte_1",
            "run_id": store.current_run_id,
        })

        store.save_decision({
            "decision_id": "D0002",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "4-digit DN",
            "context": {"dn_length": 4, "dn": "1001"},
            "options": [
                {"id": "e164", "label": "E.164", "impact": "National"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_gte_2",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DN_AMBIGUOUS",
                    "match": {"dn_length_gte": 10},
                    "choice": "e164",
                },
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        assert store.get_decision("D0001")["chosen_option"] == "e164"
        assert store.get_decision("D0002")["chosen_option"] is None

    def test_match_with_contains_suffix(self) -> None:
        """Match with _contains: substring match on context string."""
        store = _make_store()

        store.save_decision({
            "decision_id": "D0001",
            "type": "FEATURE_APPROXIMATION",
            "severity": "MEDIUM",
            "summary": "CTI RP with lobby script",
            "context": {"script_name": "aa_lobby_greeting.aef"},
            "options": [
                {"id": "auto_attendant", "label": "AA", "impact": "Convert to AA"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_contains_1",
            "run_id": store.current_run_id,
        })

        store.save_decision({
            "decision_id": "D0002",
            "type": "FEATURE_APPROXIMATION",
            "severity": "MEDIUM",
            "summary": "CTI RP with complex script",
            "context": {"script_name": "complex_ivr_routing.aef"},
            "options": [
                {"id": "auto_attendant", "label": "AA", "impact": "Convert to AA"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_contains_2",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "FEATURE_APPROXIMATION",
                    "match": {"script_name_contains": "lobby"},
                    "choice": "auto_attendant",
                },
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        assert store.get_decision("D0001")["chosen_option"] == "auto_attendant"
        assert store.get_decision("D0002")["chosen_option"] is None

    def test_match_multiple_fields_and_logic(self) -> None:
        """Multiple match fields use AND logic — all must match."""
        store = _make_store()

        # Matches both cucm_model AND compatibility_tier
        store.save_decision({
            "decision_id": "D0001",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Convertible 7841",
            "context": {"cucm_model": "7841", "compatibility_tier": "convertible"},
            "options": [
                {"id": "convert", "label": "Convert", "impact": "Convert"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_and_1",
            "run_id": store.current_run_id,
        })

        # Matches cucm_model but NOT compatibility_tier
        store.save_decision({
            "decision_id": "D0002",
            "type": "DEVICE_FIRMWARE_CONVERTIBLE",
            "severity": "MEDIUM",
            "summary": "Incompatible 7841",
            "context": {"cucm_model": "7841", "compatibility_tier": "incompatible"},
            "options": [
                {"id": "convert", "label": "Convert", "impact": "Convert"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_and_2",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DEVICE_FIRMWARE_CONVERTIBLE",
                    "match": {
                        "cucm_model": ["7841", "7861"],
                        "compatibility_tier": "convertible",
                    },
                    "choice": "convert",
                },
            ]
        }
        count = apply_auto_rules(store, config)

        assert count == 1
        assert store.get_decision("D0001")["chosen_option"] == "convert"
        assert store.get_decision("D0002")["chosen_option"] is None

    def test_match_field_not_in_context_skips(self) -> None:
        """If a match key references a context field that doesn't exist,
        the rule is skipped (no crash)."""
        store = _make_store()

        store.save_decision({
            "decision_id": "D0001",
            "type": "DEVICE_INCOMPATIBLE",
            "severity": "HIGH",
            "summary": "No cucm_model in context",
            "context": {"canonical_id": "d:1"},  # No cucm_model field
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_missing_key_1",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DEVICE_INCOMPATIBLE",
                    "match": {"cucm_model": ["7911"]},
                    "choice": "skip",
                },
            ]
        }
        # Should not crash — just skip the rule
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D0001")["chosen_option"] is None

    def test_lte_with_non_numeric_context_skips_gracefully(self) -> None:
        """Non-numeric context value with _lte operator skips (no crash)."""
        store = _make_store()

        store.save_decision({
            "decision_id": "D0001",
            "type": "DN_AMBIGUOUS",
            "severity": "LOW",
            "summary": "DN with string length",
            "context": {"dn_length": "not_a_number", "dn": "abc"},
            "options": [
                {"id": "extension_only", "label": "Extension", "impact": "Internal"},
                {"id": "skip", "label": "Skip", "impact": "Skip"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_non_numeric_1",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {
                    "type": "DN_AMBIGUOUS",
                    "match": {"dn_length_lte": 4},
                    "choice": "extension_only",
                },
            ]
        }
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D0001")["chosen_option"] is None


# ---------------------------------------------------------------------------
# Preview API + reason field + resolved_by marker + regression guards
# ---------------------------------------------------------------------------


class TestPreviewAutoRules:
    """Tests for preview_auto_rules() — pure-read matcher preview.

    preview_auto_rules walks the same matcher logic as apply_auto_rules
    but yields (decision, auto_choice, auto_reason) without mutating the
    store. Both functions share the same internal _iter_matching_resolutions
    generator so they cannot drift on matcher semantics.
    """

    def test_preview_auto_rules_returns_pending_only(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(
            store,
            "D0002",
            dec_type="DEVICE_INCOMPATIBLE",
            chosen_option="skip",
            resolved_by="user",
        )

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)

        ids = {d["decision_id"] for d in result}
        assert ids == {"D0001"}
        # Pure read: store is unchanged.
        assert store.get_decision("D0001")["chosen_option"] is None

    def test_preview_auto_rules_skips_resolved_decisions(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(
            store,
            "D0001",
            dec_type="DEVICE_INCOMPATIBLE",
            chosen_option="manual",
            resolved_by="user",
        )

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        assert result == []

    def test_preview_auto_rules_returns_auto_choice_and_reason(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        assert len(result) == 1
        d = result[0]
        assert d["auto_choice"] == "skip"
        assert d["auto_reason"]  # non-empty synthesized reason

    def test_preview_auto_rules_uses_rule_reason_field_when_present(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {
                    "type": "DEVICE_INCOMPATIBLE",
                    "choice": "skip",
                    "reason": "No migration path exists for this model",
                },
            ]
        }
        result = preview_auto_rules(store, config)
        assert result[0]["auto_reason"] == "No migration path exists for this model"

    def test_preview_auto_rules_falls_back_to_synthesized_reason(self) -> None:
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        result = preview_auto_rules(store, config)
        reason = result[0]["auto_reason"]
        # Synthesized form must mention both the type and the choice.
        assert "DEVICE_INCOMPATIBLE" in reason
        assert "skip" in reason

    def test_preview_auto_rules_falls_back_when_reason_is_non_string(self, caplog) -> None:
        """Non-string reason → fall back to synthesized form and log a warning."""
        import logging
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_FIRMWARE_CONVERTIBLE")

        config = {
            "auto_rules": [
                # Non-string reason: list
                {"type": "DEVICE_INCOMPATIBLE", "choice": "skip",
                 "reason": ["a", "b"]},
                # Non-string reason: dict
                {"type": "DEVICE_FIRMWARE_CONVERTIBLE", "choice": "convert",
                 "reason": {"x": 1}},
            ]
        }
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.transform.rules"):
            result = preview_auto_rules(store, config)

        # Both decisions are still previewed (bad reason doesn't break matching).
        assert len(result) == 2
        for d in result:
            # Synthesized fallback, not the raw bad value.
            assert isinstance(d["auto_reason"], str)
            assert d["auto_reason"]

        # At least one warning about a non-string reason was logged.
        warnings = [
            r for r in caplog.records
            if "reason" in r.getMessage().lower() and r.levelname == "WARNING"
        ]
        assert warnings, f"Expected a non-string reason warning, got {caplog.records}"

    def test_preview_auto_rules_skips_invalid_choices(self) -> None:
        """Option-validation parity with apply_auto_rules: rules whose
        choice isn't in the decision's options are not yielded."""
        from wxcli.migration.transform.rules import preview_auto_rules

        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {
            "auto_rules": [
                {"type": "DEVICE_INCOMPATIBLE", "choice": "nonexistent_choice"},
            ]
        }
        result = preview_auto_rules(store, config)
        assert result == []

    def test_apply_auto_rules_uses_resolved_by_auto_rule(self) -> None:
        """Regression guard: the resolved_by marker must be 'auto_rule'
        (not the legacy 'auto_apply') for every rule-driven resolution."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        apply_auto_rules(store, config)

        dec = store.get_decision("D0001")
        assert dec["resolved_by"] == "auto_rule"

    def test_calling_permission_mismatch_with_users_not_silently_skipped(self) -> None:
        """Regression guard for the Bug F silent data-loss case.

        Before the unification, decide --apply-auto ran _check_auto_apply
        which read a nonexistent key and always treated user_count as 0 —
        silently skipping every pending CALLING_PERMISSION_MISMATCH. After
        the unification, the default rule (match on assigned_users_count == 0)
        correctly does NOT match a decision with assigned_users_count == 5.
        """
        store = _make_store()
        store.save_decision({
            "decision_id": "D_CPM_01",
            "type": "CALLING_PERMISSION_MISMATCH",
            "severity": "MEDIUM",
            "summary": "Permission profile with 5 users",
            "context": {"assigned_users_count": 5, "profile_name": "Internal"},
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Not migrated"},
                {"id": "manual", "label": "Manual", "impact": "Manual"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_cpm_01",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {"type": "CALLING_PERMISSION_MISMATCH",
                 "match": {"assigned_users_count": 0},
                 "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D_CPM_01")["chosen_option"] is None

    def test_md_rule_does_not_fire_when_device_is_compatible(self) -> None:
        """The new default MD rule must not fire when
        is_on_incompatible_device is False or absent."""
        store = _make_store()
        store.save_decision({
            "decision_id": "D_MD_01",
            "type": "MISSING_DATA",
            "severity": "MEDIUM",
            "summary": "phone missing mac",
            "context": {
                "object_type": "device",
                "canonical_id": "phone:001",
                "missing_fields": ["mac"],
                "is_on_incompatible_device": False,
            },
            "options": [
                {"id": "skip", "label": "Skip", "impact": "Excluded"},
                {"id": "provide_data", "label": "Provide", "impact": "Supply"},
            ],
            "chosen_option": None,
            "resolved_at": None,
            "resolved_by": None,
            "fingerprint": "fp_md_01",
            "run_id": store.current_run_id,
        })

        config = {
            "auto_rules": [
                {"type": "MISSING_DATA",
                 "match": {"is_on_incompatible_device": True},
                 "choice": "skip"},
            ]
        }
        count = apply_auto_rules(store, config)
        assert count == 0
        assert store.get_decision("D_MD_01")["chosen_option"] is None

    def test_analyze_then_apply_auto_is_no_op(self) -> None:
        """Idempotent re-run: running apply_auto_rules twice resolves N the
        first time and 0 the second time."""
        store = _make_store()
        _seed_decision(store, "D0001", dec_type="DEVICE_INCOMPATIBLE")
        _seed_decision(store, "D0002", dec_type="DEVICE_INCOMPATIBLE")

        config = {"auto_rules": [{"type": "DEVICE_INCOMPATIBLE", "choice": "skip"}]}
        first = apply_auto_rules(store, config)
        second = apply_auto_rules(store, config)
        assert first == 2
        assert second == 0


class TestDefaultAutoRulesMissingDataEntry:
    """Sanity checks for the new is_on_incompatible_device default rule."""

    def test_default_has_md_incompatible_entry(self) -> None:
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES

        matches = [
            r for r in DEFAULT_AUTO_RULES
            if r.get("type") == "MISSING_DATA"
            and r.get("match", {}).get("is_on_incompatible_device") is True
        ]
        assert len(matches) == 1, (
            f"Expected exactly one MISSING_DATA/is_on_incompatible_device "
            f"rule in DEFAULT_AUTO_RULES, got {len(matches)}"
        )
        rule = matches[0]
        assert rule["choice"] == "skip"
        # Reason is optional but recommended for markdown clarity.
        if "reason" in rule:
            assert isinstance(rule["reason"], str)
            assert rule["reason"]
