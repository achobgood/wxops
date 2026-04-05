"""Tests for new advisory patterns (21-26) and modified recommendation rules.

Uses real :memory: SQLite store, no mocks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.models import (
    MigrationObject,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore
from wxcli.migration.advisory.advisory_patterns import (
    detect_mixed_css,
    detect_cumulative_virtual_line_consumption,
    detect_user_oauth_required,
    detect_trunk_type_selection,
    detect_intercluster_trunks,
    detect_legacy_gateway_protocols,
)
from wxcli.migration.advisory.recommendation_rules import (
    recommend_feature_approximation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prov(name: str = "test") -> Provenance:
    return Provenance(
        source_system="cucm",
        source_id=f"uuid-{name}",
        source_name=name,
        extracted_at=datetime.now(timezone.utc),
    )


def _store() -> MigrationStore:
    return MigrationStore(":memory:")


def _insert_obj(store: MigrationStore, canonical_id: str, object_type: str,
                extra: dict | None = None) -> None:
    """Insert an object into the store with the given type."""
    obj = MigrationObject(
        canonical_id=canonical_id,
        provenance=_prov(canonical_id),
        status=MigrationStatus.ANALYZED,
        pre_migration_state=extra or {},
    )
    # We need to manually set the object type since MigrationObject doesn't
    # have a type field — the store derives it from the class. We'll use
    # a direct SQL insert for test flexibility.
    import json
    data = obj.model_dump()
    if extra:
        data.update(extra)
    data_json = json.dumps(data, default=str)
    store.conn.execute(
        """INSERT OR REPLACE INTO objects
           (canonical_id, object_type, status, data, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (canonical_id, object_type, "analyzed", data_json,
         datetime.now(timezone.utc).isoformat(),
         datetime.now(timezone.utc).isoformat()),
    )
    store.conn.commit()


def _insert_decision(store: MigrationStore, decision_id: str, dec_type: str,
                     recommendation: str | None = None, context: dict | None = None) -> None:
    """Insert a decision into the store."""
    import json
    store.conn.execute(
        """INSERT OR REPLACE INTO decisions
           (decision_id, type, severity, summary, context, options,
            fingerprint, run_id, recommendation, recommendation_reasoning)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (decision_id, dec_type, "MEDIUM", f"Test {dec_type}",
         json.dumps(context or {}), json.dumps([]),
         f"fp-{decision_id}", "run-1", recommendation, None),
    )
    store.conn.commit()


# ===================================================================
# Pattern 21: Mixed CSS Detection
# ===================================================================

class TestMixedCSS:
    """Tests for detect_mixed_css."""

    def test_no_csses_returns_empty(self) -> None:
        store = _store()
        assert detect_mixed_css(store) == []

    def test_pure_blocking_css_ignored(self) -> None:
        """CSSes with only blocking patterns are covered by Pattern 1, not Pattern 21."""
        store = _store()
        _insert_obj(store, "css:CSS-Block", "calling_search_space", {"name": "CSS-Block"})
        _insert_obj(store, "partition:PT-Block", "route_partition")
        _insert_obj(store, "rp:block-intl", "route_pattern",
                    {"pre_migration_state": {"blockEnable": True}})
        store.add_cross_ref("css:CSS-Block", "partition:PT-Block", "css_contains_partition")
        store.add_cross_ref("partition:PT-Block", "rp:block-intl", "partition_has_pattern")
        assert detect_mixed_css(store) == []

    def test_pure_routing_css_ignored(self) -> None:
        """CSSes with only routing patterns should not fire."""
        store = _store()
        _insert_obj(store, "css:CSS-Route", "calling_search_space", {"name": "CSS-Route"})
        _insert_obj(store, "partition:PT-Route", "route_partition")
        _insert_obj(store, "rp:route-local", "route_pattern",
                    {"pre_migration_state": {"blockEnable": False}})
        store.add_cross_ref("css:CSS-Route", "partition:PT-Route", "css_contains_partition")
        store.add_cross_ref("partition:PT-Route", "rp:route-local", "partition_has_pattern")
        assert detect_mixed_css(store) == []

    def test_mixed_css_fires(self) -> None:
        """CSS with both routing and blocking partitions should fire."""
        store = _store()
        _insert_obj(store, "css:CSS-Mixed", "calling_search_space", {"name": "CSS-Mixed"})
        # Routing partition
        _insert_obj(store, "partition:PT-Internal", "route_partition")
        _insert_obj(store, "rp:internal", "route_pattern",
                    {"pre_migration_state": {"blockEnable": False}})
        store.add_cross_ref("css:CSS-Mixed", "partition:PT-Internal", "css_contains_partition")
        store.add_cross_ref("partition:PT-Internal", "rp:internal", "partition_has_pattern")
        # Blocking partition
        _insert_obj(store, "partition:PT-BlockIntl", "route_partition")
        _insert_obj(store, "rp:block-intl", "route_pattern",
                    {"pre_migration_state": {"blockEnable": True}})
        store.add_cross_ref("css:CSS-Mixed", "partition:PT-BlockIntl", "css_contains_partition")
        store.add_cross_ref("partition:PT-BlockIntl", "rp:block-intl", "partition_has_pattern")

        findings = detect_mixed_css(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "mixed_css_routing_restriction"
        assert findings[0].severity == "HIGH"
        assert findings[0].category == "rebuild"
        assert "css:CSS-Mixed" in findings[0].affected_objects


# ===================================================================
# Pattern 22: Cumulative Virtual Line Counter
# ===================================================================

class TestCumulativeVirtualLine:
    """Tests for detect_cumulative_virtual_line_consumption."""

    def test_no_virtual_lines_returns_empty(self) -> None:
        store = _store()
        assert detect_cumulative_virtual_line_consumption(store) == []

    def test_low_count_under_threshold(self) -> None:
        """Under 5 virtual lines total → no advisory."""
        store = _store()
        _insert_decision(store, "d1", "SHARED_LINE_COMPLEX", recommendation="virtual_extension")
        _insert_decision(store, "d2", "SHARED_LINE_COMPLEX", recommendation="shared_line")
        assert detect_cumulative_virtual_line_consumption(store) == []

    def test_medium_count_fires(self) -> None:
        """10+ virtual lines → fires with LOW or MEDIUM severity."""
        store = _store()
        for i in range(10):
            _insert_decision(store, f"d{i}", "SHARED_LINE_COMPLEX",
                            recommendation="virtual_extension")
        findings = detect_cumulative_virtual_line_consumption(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "cumulative_virtual_line_consumption"
        assert findings[0].severity in ("LOW", "MEDIUM")

    def test_high_count_warns(self) -> None:
        """30+ virtual lines → MEDIUM severity."""
        store = _store()
        for i in range(30):
            _insert_decision(store, f"d{i}", "DN_AMBIGUOUS",
                            recommendation="virtual_extension")
        findings = detect_cumulative_virtual_line_consumption(store)
        assert len(findings) == 1
        assert findings[0].severity == "MEDIUM"

    def test_very_high_count_critical(self) -> None:
        """100+ virtual lines → HIGH severity."""
        store = _store()
        for i in range(105):
            _insert_decision(store, f"d{i}", "SHARED_LINE_COMPLEX",
                            recommendation="virtual_extension")
        findings = detect_cumulative_virtual_line_consumption(store)
        assert len(findings) == 1
        assert findings[0].severity == "HIGH"

    def test_includes_existing_vl_objects(self) -> None:
        """Count includes virtual_line objects already in the store."""
        store = _store()
        for i in range(6):
            _insert_obj(store, f"vl:{i}", "virtual_line")
        findings = detect_cumulative_virtual_line_consumption(store)
        assert len(findings) == 1
        assert "6" in findings[0].detail


# ===================================================================
# Pattern 23: User OAuth Required
# ===================================================================

class TestUserOAuthRequired:
    """Tests for detect_user_oauth_required."""

    def test_no_users_returns_empty(self) -> None:
        store = _store()
        assert detect_user_oauth_required(store) == []

    def test_users_without_user_only_settings_ignored(self) -> None:
        """Users with no user-only settings should not fire."""
        store = _store()
        _insert_obj(store, "user:jdoe", "user", {"call_settings": {"callForwarding": True}})
        assert detect_user_oauth_required(store) == []

    def test_snr_objects_trigger(self) -> None:
        """Single number reach objects map to simultaneousRing → fires."""
        store = _store()
        _insert_obj(store, "snr:jdoe", "single_number_reach",
                    {"user_canonical_id": "user:jdoe"})
        findings = detect_user_oauth_required(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "user_oauth_required"
        assert findings[0].severity == "HIGH"
        assert "user:jdoe" in findings[0].affected_objects

    def test_user_with_simring_setting(self) -> None:
        """User with simultaneousRing in call_settings → fires."""
        store = _store()
        _insert_obj(store, "user:jsmith", "user",
                    {"call_settings": {"simultaneousRing": {"enabled": True}}})
        findings = detect_user_oauth_required(store)
        assert len(findings) == 1

    def test_phone_line_simring_cycles_triggers(self) -> None:
        """Phone with simultaneousRingNumRingCycles on a line → resolves owner and fires."""
        store = _store()
        _insert_obj(store, "user:bwayne", "user", {"cucm_userid": "bwayne"})
        _insert_obj(store, "phone:SEP112233445566", "phone", {
            "pre_migration_state": {
                "ownerUserName": "bwayne",
                "lines": [{"simultaneousRingNumRingCycles": "3"}],
            },
        })
        findings = detect_user_oauth_required(store)
        assert len(findings) == 1
        assert "user:bwayne" in findings[0].affected_objects


# ===================================================================
# Pattern 24: Trunk Type Selection
# ===================================================================

class TestTrunkTypeSelection:
    """Tests for detect_trunk_type_selection."""

    def test_no_trunks_returns_empty(self) -> None:
        store = _store()
        assert detect_trunk_type_selection(store) == []

    def test_trunks_with_type_set_ignored(self) -> None:
        """Trunks that already have trunk_type don't need selection."""
        store = _store()
        _insert_obj(store, "trunk:sbc1", "trunk",
                    {"trunk_type": "REGISTERING", "name": "SBC-CUBE"})
        assert detect_trunk_type_selection(store) == []

    def test_cisco_cube_auto_classified(self) -> None:
        """Trunk with CUBE in name → auto-classified as REGISTERING."""
        store = _store()
        _insert_obj(store, "trunk:cube1", "trunk",
                    {"name": "ISR-CUBE-Gateway", "trunk_type": None})
        assert detect_trunk_type_selection(store) == []

    def test_audiocodes_auto_classified(self) -> None:
        """Trunk with AudioCodes in name → auto-classified as CERTIFICATE_BASED."""
        store = _store()
        _insert_obj(store, "trunk:ac1", "trunk",
                    {"name": "AudioCodes-Mediant", "trunk_type": None})
        assert detect_trunk_type_selection(store) == []

    def test_unknown_trunk_fires(self) -> None:
        """Trunk with no recognizable SBC pattern → needs selection."""
        store = _store()
        _insert_obj(store, "trunk:pstn1", "trunk",
                    {"name": "PSTN-Primary", "trunk_type": None, "address": "10.0.0.1"})
        findings = detect_trunk_type_selection(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "trunk_type_selection"
        assert findings[0].severity == "CRITICAL"
        assert "trunk:pstn1" in findings[0].affected_objects

    def test_isr_word_boundary_no_false_positive(self) -> None:
        """Trunk named 'First-Trunk' should NOT match \\bisr\\b pattern."""
        store = _store()
        _insert_obj(store, "trunk:first1", "trunk",
                    {"name": "First-Trunk", "trunk_type": None, "address": "10.0.0.5"})
        findings = detect_trunk_type_selection(store)
        assert len(findings) == 1  # Should fire as unknown, NOT auto-classify as CUBE
        assert "trunk:first1" in findings[0].affected_objects


# ===================================================================
# Pattern 25: Inter-Cluster Trunk Detection
# ===================================================================

class TestInterclusterTrunks:
    """Tests for detect_intercluster_trunks."""

    def test_no_trunks_returns_empty(self) -> None:
        store = _store()
        assert detect_intercluster_trunks(store) == []

    def test_regular_trunk_ignored(self) -> None:
        """Non-ICT trunks should not fire."""
        store = _store()
        _insert_obj(store, "trunk:pstn1", "trunk",
                    {"name": "PSTN-Primary", "pre_migration_state": {}})
        assert detect_intercluster_trunks(store) == []

    def test_ict_name_detected(self) -> None:
        """Trunk named with 'Inter-Cluster' fires."""
        store = _store()
        _insert_obj(store, "trunk:ict1", "trunk",
                    {"name": "Inter-Cluster-Trunk-to-HQ",
                     "pre_migration_state": {"description": "ICT to main cluster"}})
        findings = detect_intercluster_trunks(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "intercluster_trunk_detection"
        assert findings[0].severity == "HIGH"

    def test_emcc_trunk_detected(self) -> None:
        """EMCC (Extension Mobility Cross Cluster) trunk fires."""
        store = _store()
        _insert_obj(store, "trunk:emcc1", "trunk",
                    {"name": "EMCC-Trunk",
                     "pre_migration_state": {"description": "Extension Mobility Cross Cluster"}})
        findings = detect_intercluster_trunks(store)
        assert len(findings) == 1


# ===================================================================
# Pattern 26: Legacy Gateway Protocols
# ===================================================================

class TestLegacyGatewayProtocols:
    """Tests for detect_legacy_gateway_protocols."""

    def test_no_gateways_returns_empty(self) -> None:
        store = _store()
        assert detect_legacy_gateway_protocols(store) == []

    def test_sip_trunk_ignored(self) -> None:
        """SIP trunks should not fire."""
        store = _store()
        _insert_obj(store, "trunk:sip1", "trunk",
                    {"name": "SIP-Trunk", "pre_migration_state": {"protocol": "SIP"}})
        assert detect_legacy_gateway_protocols(store) == []

    def test_mgcp_gateway_detected(self) -> None:
        """MGCP gateway fires."""
        store = _store()
        _insert_obj(store, "gw:vg310", "gateway",
                    {"name": "VG310-Analog",
                     "pre_migration_state": {"protocol": "MGCP", "product": "VG310"}})
        findings = detect_legacy_gateway_protocols(store)
        assert len(findings) == 1
        assert findings[0].pattern_name == "legacy_gateway_protocols"
        assert "MGCP" in findings[0].detail

    def test_h323_gateway_detected(self) -> None:
        """H.323 gateway fires."""
        store = _store()
        _insert_obj(store, "gw:h323-gk", "gateway",
                    {"name": "H323-Gatekeeper",
                     "pre_migration_state": {"protocol": "H.323"}})
        findings = detect_legacy_gateway_protocols(store)
        assert len(findings) == 1
        assert "H.323" in findings[0].detail

    def test_fxs_device_detected(self) -> None:
        """Device with FXS/analog pattern fires."""
        store = _store()
        _insert_obj(store, "dev:analog1", "device",
                    {"model": "VG224", "cucm_protocol": "MGCP"})
        findings = detect_legacy_gateway_protocols(store)
        assert len(findings) == 1


# ===================================================================
# Modified Recommendation: Feature Approximation (routing-type-aware)
# ===================================================================

class TestFeatureApproximationRoutingAware:
    """Tests for routing-type-aware agent cap in recommend_feature_approximation."""

    def test_broadcast_55_agents_splits(self) -> None:
        """Broadcast algorithm with 55 agents → split (simultaneous cap)."""
        result = recommend_feature_approximation(
            {"agent_count": 55, "algorithm": "Broadcast", "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "split"
        assert "Simultaneous" in result[1]

    def test_circular_55_agents_no_split(self) -> None:
        """Circular algorithm with 55 agents → NOT split (priority cap is 1000)."""
        result = recommend_feature_approximation(
            {"agent_count": 55, "algorithm": "Circular", "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "call_queue"  # Queue features detected, under 1000 cap

    def test_circular_1001_agents_splits(self) -> None:
        """Circular algorithm with 1001 agents → split (exceeds 1000 cap)."""
        result = recommend_feature_approximation(
            {"agent_count": 1001, "algorithm": "Circular", "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "split"

    def test_explicit_target_routing_override(self) -> None:
        """Explicit target_routing_type=SIMULTANEOUS overrides algorithm inference."""
        result = recommend_feature_approximation(
            {"agent_count": 55, "algorithm": "Circular",
             "target_routing_type": "SIMULTANEOUS", "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "split"
        assert "Simultaneous" in result[1]

    def test_under_50_agents_no_split_regardless(self) -> None:
        """Under 50 agents → never split, regardless of routing type."""
        result = recommend_feature_approximation(
            {"agent_count": 45, "algorithm": "Broadcast", "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "call_queue"

    def test_5_8_agents_ambiguous_still_returns_none(self) -> None:
        """5-8 agents, no queue, non-top-down → still ambiguous."""
        result = recommend_feature_approximation(
            {"agent_count": 6, "algorithm": "Circular", "has_queue_features": False},
            [],
        )
        assert result is None

    def test_none_algorithm_51_agents_splits_with_assumed_note(self) -> None:
        """None algorithm + 51 agents → split with '(assumed simultaneous)' note."""
        result = recommend_feature_approximation(
            {"agent_count": 51, "algorithm": None, "has_queue_features": True},
            [],
        )
        assert result is not None
        assert result[0] == "split"
        assert "assumed simultaneous" in result[1]


# ===================================================================
# Default Auto Rules
# ===================================================================

class TestDefaultAutoRules:
    """Tests for DEFAULT_AUTO_RULES in cucm_config."""

    def test_default_config_has_auto_rules(self) -> None:
        """DEFAULT_CONFIG ships with non-empty auto_rules."""
        from wxcli.commands.cucm_config import DEFAULT_CONFIG
        rules = DEFAULT_CONFIG["auto_rules"]
        assert len(rules) >= 5  # At least the 7 default rules

    def test_default_rules_have_required_fields(self) -> None:
        """Each default rule has type and choice."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES
        for rule in DEFAULT_AUTO_RULES:
            assert "type" in rule, f"Rule missing 'type': {rule}"
            assert "choice" in rule, f"Rule missing 'choice': {rule}"

    def test_device_incompatible_rule_skips(self) -> None:
        """DEVICE_INCOMPATIBLE default rule → skip."""
        from wxcli.commands.cucm_config import DEFAULT_AUTO_RULES
        di_rules = [r for r in DEFAULT_AUTO_RULES if r["type"] == "DEVICE_INCOMPATIBLE"]
        assert len(di_rules) == 1
        assert di_rules[0]["choice"] == "skip"


# ===================================================================
# Complexity Score Calibration Flag
# ===================================================================

class TestScoreCalibrationFlag:
    """Tests for UNCALIBRATED complexity score disclaimer."""

    def test_score_result_has_calibrated_field(self) -> None:
        # Import score.py directly to avoid report/__init__.py chain (needs zeep)
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location(
            "score_direct",
            "src/wxcli/migration/report/score.py",
        )
        score_mod = importlib.util.module_from_spec(spec)
        # Temporarily add to sys.modules so relative imports work
        sys.modules["score_direct"] = score_mod
        spec.loader.exec_module(score_mod)
        result = score_mod.ScoreResult()
        assert result.calibrated == score_mod.SCORE_CALIBRATED
        del sys.modules["score_direct"]

    def test_score_currently_uncalibrated(self) -> None:
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location(
            "score_direct2",
            "src/wxcli/migration/report/score.py",
        )
        score_mod = importlib.util.module_from_spec(spec)
        sys.modules["score_direct2"] = score_mod
        spec.loader.exec_module(score_mod)
        assert score_mod.SCORE_CALIBRATED is False
        del sys.modules["score_direct2"]
