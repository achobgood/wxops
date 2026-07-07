"""Tests for per-decision recommendation rules.

Each DecisionType gets a function that examines context + options and returns
(option_id, reasoning) or None.

Reference: spec section 5 for expected behavior per type.
"""
from wxcli.migration.advisory.recommendation_rules import (
    recommend_device_firmware_convertible,
    recommend_missing_data,
    recommend_number_conflict,
    recommend_duplicate_user,
    recommend_workspace_license_tier,
    recommend_hotdesk_dn_conflict,
    recommend_device_incompatible,
    recommend_dn_ambiguous,
    recommend_extension_conflict,
    recommend_location_ambiguous,
    recommend_workspace_type_uncertain,
    recommend_feature_approximation,
    recommend_shared_line_complex,
    recommend_css_routing_mismatch,
    recommend_calling_permission_mismatch,
    recommend_voicemail_incompatible,
    recommend_audio_asset_manual,
)


class TestDeviceFirmwareConvertible:
    def test_always_recommends_convert(self):
        r = recommend_device_firmware_convertible({"cucm_model": "8845"}, [])
        assert r is not None
        assert r[0] == "convert"
        assert "8845" in r[1]

    def test_srst_adds_warning(self):
        r = recommend_device_firmware_convertible(
            {"cucm_model": "8845", "has_srst": True}, [])
        assert r[0] == "convert"
        assert "Survivable Gateway" in r[1]

    def test_no_srst_no_warning(self):
        r = recommend_device_firmware_convertible(
            {"cucm_model": "7841"}, [])
        assert "Survivable" not in r[1]


class TestMissingData:
    def test_leaf_object_missing_fields_skips(self):
        """Objects with no dependents can be safely skipped."""
        r = recommend_missing_data({"missing_fields": ["email", "location"], "dependent_count": 0}, [])
        assert r[0] == "skip"
        assert "email" in r[1]

    def test_object_with_dependents_returns_none(self):
        """Objects with dependents should NOT auto-skip — force human review."""
        r = recommend_missing_data({"missing_fields": ["address"], "dependent_count": 5}, [])
        assert r is None

    def test_infrastructure_object_returns_none(self):
        """Locations, trunks, route groups always force review."""
        r = recommend_missing_data({"missing_fields": ["address"], "object_type": "location"}, [])
        assert r is None

    def test_no_context_skips(self):
        r = recommend_missing_data({}, [])
        assert r[0] == "skip"


class TestNumberConflict:
    def test_same_owner_auto_resolves(self):
        r = recommend_number_conflict({"same_owner": True}, [])
        assert r[0] == "auto_resolve"

    def test_different_owner_keeps_existing(self):
        r = recommend_number_conflict({
            "existing_owner": "alice@co.com", "cucm_owner": "bob@co.com"
        }, [])
        assert r[0] == "keep_existing"
        assert "alice" in r[1]


class TestDuplicateUser:
    def test_email_match_merges(self):
        r = recommend_duplicate_user({"email_match": True, "email": "a@b.com"}, [])
        assert r[0] == "merge"
        assert "a@b.com" in r[1]

    def test_name_only_keeps_both(self):
        r = recommend_duplicate_user({"email_match": False}, [])
        assert r[0] == "keep_both"

    def test_userid_match_merges(self):
        r = recommend_duplicate_user(
            {"userid_match": True, "email_match": False}, [])
        assert r[0] == "merge"


class TestWorkspaceLicenseTier:
    def test_basic_features_only(self):
        r = recommend_workspace_license_tier(
            {"features_detected": ["musicOnHold", "doNotDisturb"]}, [])
        assert r[0] == "basic"

    def test_professional_features(self):
        r = recommend_workspace_license_tier(
            {"features_detected": ["callForwarding", "monitoring"]}, [])
        assert r[0] == "professional"

    def test_empty_defaults_basic(self):
        r = recommend_workspace_license_tier({"features_detected": []}, [])
        assert r[0] == "basic"


class TestHotdeskDnConflict:
    def test_always_keep_primary(self):
        r = recommend_hotdesk_dn_conflict({}, [])
        assert r[0] == "keep_primary"


class TestDeviceIncompatible:
    def test_7811_recommends_9841(self):
        r = recommend_device_incompatible({"cucm_model": "7811"}, [])
        assert r is not None
        assert r[0] == "replace"
        assert "9841" in r[1]

    def test_7832_recommends_conference(self):
        r = recommend_device_incompatible({"cucm_model": "7832"}, [])
        assert r[0] == "replace"
        assert "conference" in r[1].lower() or "Room" in r[1]

    def test_unknown_model_returns_none(self):
        r = recommend_device_incompatible({"cucm_model": "XYZZY_9999"}, [])
        assert r is None


class TestDnAmbiguous:
    def test_single_owner_assigns(self):
        r = recommend_dn_ambiguous({"owner_count": 1, "owner_name": "Alice"}, [])
        assert r[0] == "assign"
        assert "Alice" in r[1]

    def test_primary_owner_assigns(self):
        r = recommend_dn_ambiguous({"owner_count": 3, "primary_owner": "Bob"}, [])
        assert r[0] == "assign"
        assert "Bob" in r[1]

    def test_no_primary_returns_none(self):
        r = recommend_dn_ambiguous({"owner_count": 3}, [])
        assert r is None


class TestExtensionConflict:
    def test_more_appearances_keeps(self):
        r = recommend_extension_conflict({
            "ext_a": "1001", "ext_a_appearances": 5, "owner_a": "Alice",
            "ext_b": "1001", "ext_b_appearances": 2, "owner_b": "Bob",
        }, [])
        assert r[0] == "keep_a"
        assert "Alice" in r[1]

    def test_b_more_appearances(self):
        r = recommend_extension_conflict({
            "ext_a": "1001", "ext_a_appearances": 1, "owner_a": "Alice",
            "ext_b": "1001", "ext_b_appearances": 4, "owner_b": "Bob",
        }, [])
        assert r[0] == "keep_b"

    def test_equal_returns_none(self):
        r = recommend_extension_conflict({
            "ext_a_appearances": 2, "ext_b_appearances": 2,
        }, [])
        assert r is None


class TestLocationAmbiguous:
    def test_same_tz_region_consolidates(self):
        r = recommend_location_ambiguous({
            "timezone": "America/Chicago", "region": "US-Central",
            "site_code": "DAL", "dp_names": ["DP_DAL1", "DP_DAL2"],
        }, [])
        assert r[0] == "consolidate"

    def test_different_region_returns_none(self):
        r = recommend_location_ambiguous({
            "same_timezone": True, "same_region": False,
        }, [])
        assert r is None

    def test_all_match_consolidates(self):
        r = recommend_location_ambiguous({
            "timezone": "US/Eastern", "region": "US-East",
            "site_code": "NYC",
        }, [])
        assert r[0] == "consolidate"


class TestWorkspaceTypeUncertain:
    def test_conference_phone_recommends_conference_room(self):
        r = recommend_workspace_type_uncertain({"cucm_model": "7832"}, [])
        assert r[0] == "conference_room"

    def test_desk_phone_no_owner_recommends_common_area(self):
        r = recommend_workspace_type_uncertain(
            {"cucm_model": "8841", "has_owner": False}, [])
        assert r[0] == "common_area"

    def test_ambiguous_returns_none(self):
        r = recommend_workspace_type_uncertain(
            {"cucm_model": "8841", "has_owner": True}, [])
        assert r is None


class TestFeatureApproximation:
    def test_queue_features_recommends_call_queue(self):
        r = recommend_feature_approximation(
            {"has_queue_features": True, "agent_count": 12}, [])
        assert r[0] == "call_queue"

    def test_many_agents_no_queue_still_recommends_cq(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 10}, [])
        assert r[0] == "call_queue"

    def test_small_group_no_queue_recommends_hg(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 3,
             "algorithm": "Top Down"}, [])
        assert r[0] == "hunt_group"

    def test_ambiguous_returns_none(self):
        r = recommend_feature_approximation(
            {"has_queue_features": False, "agent_count": 6}, [])
        assert r is None

    def test_cti_rp_simple_recommends_accept(self):
        r = recommend_feature_approximation(
            {"classification": "AUTO_ATTENDANT", "complex_script": False}, [])
        assert r[0] == "accept"

    def test_cti_rp_complex_returns_none(self):
        r = recommend_feature_approximation(
            {"classification": "AUTO_ATTENDANT", "complex_script": True}, [])
        assert r is None

    def test_agent_limit_exceeded_recommends_split(self):
        r = recommend_feature_approximation(
            {"has_queue_features": True, "agent_count": 60}, [])
        assert r[0] == "split"
        assert "50" in r[1]

    def test_cti_rp_mapper_context_shape_recommends_accept(self):
        """Integration test: CTI RP decision context produced by FeatureMapper._map_cti_route_points
        must cause the recommender to return 'accept' for simple scripts.

        Regression guard for the mapper->recommender integration gap where
        `classification` and `complex_script` were missing from the mapper's
        decision context, causing every CTI RP to receive the wrong recommendation.
        """
        # Simulate the mapper's CTI RP decision context after fix
        mapper_ctx = {
            "cti_rp_id": "cti_rp:abc123",
            "name": "Reception IVR",
            "classification": "AUTO_ATTENDANT",
            "complex_script": False,
            "reason": "cti_rp_to_auto_attendant",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None, "CTI RP context should produce a recommendation"
        assert r[0] == "accept", f"Expected 'accept', got {r[0]!r}"

    def test_cti_rp_mapper_context_complex_script_returns_none(self):
        """Regression guard: CTI RP with complex script must return None (ambiguous)."""
        mapper_ctx = {
            "cti_rp_id": "cti_rp:abc123",
            "name": "Reception IVR",
            "classification": "AUTO_ATTENDANT",
            "complex_script": True,
            "reason": "cti_rp_to_auto_attendant",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is None

    def test_large_circular_policy_uses_priority_cap(self):
        """Regression guard: a 1100-agent CIRCULAR-policy hunt pilot should be flagged
        against the 1000-agent priority-based cap, not the 50-agent simultaneous cap.

        Before fix: the rule read `algorithm` (never set by mapper), defaulted to None,
        and `None in (..., None)` returned True → always treated as simultaneous →
        always framed against the 50-cap even for priority-based policies.

        After fix: the rule reads `policy` (Webex form set by mapper) → correctly
        identifies non-SIMULTANEOUS policies → uses the 1000-cap.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Large Queue",
            "policy": "CIRCULAR",  # non-simultaneous Webex policy
            "agent_count": 1100,
            "agent_limit": 1000,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None, "agent-limit-exceeded decision should produce a recommendation"
        assert r[0] == "split", f"Expected 'split', got {r[0]!r}"
        # The reasoning must reference the 1000-cap, not the 50-cap
        assert "1000" in r[1] or "1,000" in r[1], (
            f"Expected reasoning to reference priority-based cap (1000), got: {r[1]!r}"
        )
        assert "50" not in r[1], (
            f"Reasoning should NOT mention the simultaneous cap (50) "
            f"for a CIRCULAR-policy hunt pilot. Got: {r[1]!r}"
        )

    def test_large_simultaneous_policy_uses_simultaneous_cap(self):
        """Regression guard: 60-agent SIMULTANEOUS-policy hunt pilot still uses the 50-cap.

        Also verifies the reasoning string does NOT claim "assumed simultaneous"
        when policy=SIMULTANEOUS was explicitly set by the mapper. The stale
        routing_note branch in the recommender previously fired even for
        explicit policy contexts because it only checked algorithm/target_routing.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Broadcast Pilot",
            "policy": "SIMULTANEOUS",
            "agent_count": 60,
            "agent_limit": 50,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None
        assert r[0] == "split"
        assert "50" in r[1], (
            f"Expected reasoning to reference simultaneous cap (50), got: {r[1]!r}"
        )
        assert "assumed simultaneous" not in r[1], (
            "policy=SIMULTANEOUS was explicitly detected; reasoning must not "
            f"claim it was assumed. Got: {r[1]!r}"
        )

    def test_large_regular_policy_uses_priority_cap(self):
        """Regression guard: 1100-agent REGULAR-policy (Top Down → REGULAR) uses priority cap.

        Also catches the pre-fix bug where the rule treated 'Top Down' as simultaneous.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Top Down Pilot",
            "policy": "REGULAR",
            "agent_count": 1100,
            "agent_limit": 1000,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None
        assert r[0] == "split"
        assert "1000" in r[1] or "1,000" in r[1]
        assert "50" not in r[1]

    def test_weighted_policy_uses_weighted_cap(self):
        """Regression guard: WEIGHTED policy caps at 100, not 1000.

        Pre-fix: recommender used hard-coded priority_cap=1000, so a 500-agent
        WEIGHTED hunt pilot would fire the mapper decision (500 > 100) but get
        NO recommendation back (500 < 1000). Post-fix: reads `agent_limit` from
        context, correctly recommends split against the 100 cap.
        """
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Weighted Pilot",
            "policy": "WEIGHTED",
            "agent_count": 500,
            "agent_limit": 100,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None, (
            "WEIGHTED hunt pilot exceeding cap should produce a recommendation"
        )
        assert r[0] == "split"
        assert "100" in r[1], (
            f"Expected reasoning to reference WEIGHTED cap (100), got: {r[1]!r}"
        )

    def test_uniform_policy_uses_priority_cap(self):
        """UNIFORM policy is non-simultaneous and uses the 1000 cap (priority-based)."""
        mapper_ctx = {
            "hunt_pilot_id": "hp:test",
            "name": "Uniform Pilot",
            "policy": "UNIFORM",
            "agent_count": 1100,
            "agent_limit": 1000,
            "reason": "agent_limit_exceeded",
        }
        r = recommend_feature_approximation(mapper_ctx, [])
        assert r is not None
        assert r[0] == "split"
        assert "1000" in r[1] or "1,000" in r[1]


class TestFeatureApproximationEM:
    """EM-specific branch of recommend_feature_approximation."""

    def test_simple_em_profile_recommends_accept(self):
        r = recommend_feature_approximation(
            {"classification": "EXTENSION_MOBILITY", "line_count": 1,
             "speed_dial_count": 0, "blf_count": 0},
            [],
        )
        assert r is not None
        assert r[0] == "accept"
        assert "hot desking" in r[1].lower()

    def test_multi_line_em_profile_recommends_accept(self):
        r = recommend_feature_approximation(
            {"classification": "EXTENSION_MOBILITY", "line_count": 3,
             "speed_dial_count": 0, "blf_count": 2},
            [],
        )
        assert r is not None
        assert r[0] == "accept"
        assert "primary line only" in r[1].lower() or "line" in r[1].lower()

    def test_em_with_speed_dials_recommends_accept(self):
        r = recommend_feature_approximation(
            {"classification": "EXTENSION_MOBILITY", "line_count": 1,
             "speed_dial_count": 5, "blf_count": 0},
            [],
        )
        assert r is not None
        assert r[0] == "accept"

    def test_non_em_classification_falls_through(self):
        # AUTO_ATTENDANT classification should NOT take the EM branch
        r = recommend_feature_approximation(
            {"classification": "AUTO_ATTENDANT", "complex_script": False},
            [],
        )
        assert r is not None
        assert r[0] == "accept"
        # Should hit the existing AA branch, not the EM branch


class TestSharedLineComplex:
    def test_low_count_shared_line(self):
        r = recommend_shared_line_complex({"appearance_count": 5}, [])
        assert r[0] == "shared_line"

    def test_monitoring_labels_virtual_extension(self):
        r = recommend_shared_line_complex({
            "appearance_count": 4,
            "secondary_labels": ["BLF-Sales", "Monitor-Support"]
        }, [])
        assert r[0] == "virtual_extension"

    def test_mixed_high_count_returns_none(self):
        r = recommend_shared_line_complex({
            "appearance_count": 15,
            "secondary_labels": ["Line2", "BLF-Admin"]
        }, [])
        assert r is None


class TestCssRoutingMismatch:
    def test_partition_ordering_dep_manual(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "partition_ordering",
            "pattern": "9.XXXX",
        }, [])
        assert r[0] == "manual"
        assert "partition ordering" in r[1].lower()

    def test_scope_diff_use_union(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "scope_difference",
        }, [])
        assert r[0] == "use_union"

    def test_pattern_conflict_manual(self):
        r = recommend_css_routing_mismatch({
            "mismatch_type": "pattern_conflict",
            "pattern": "9011!",
            "route_a": "GW1", "route_b": "GW2",
            "dp_a": "DP-Intl", "dp_b": "DP-Domestic",
        }, [])
        assert r[0] == "manual"


class TestCallingPermissionMismatch:
    def test_international_pattern(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "011!"
        }, [])
        assert r[0] == "INTERNATIONAL_CALL"

    def test_toll_pattern(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "1900!"
        }, [])
        assert r[0] == "PREMIUM_SERVICES_NUMBER_ONE"

    def test_unknown_pattern_returns_none(self):
        r = recommend_calling_permission_mismatch({
            "block_pattern": "5551234"
        }, [])
        assert r is None


class TestVoicemailIncompatible:
    def test_cfna_timeout_maps_ring_count(self):
        r = recommend_voicemail_incompatible({"cfna_timeout": 18}, [])
        assert r[0] == "webex_voicemail"
        assert "3" in r[1]  # 18s / 6s per ring = 3 rings

    def test_unity_settings_in_reasoning(self):
        r = recommend_voicemail_incompatible({
            "unity_features": ["greeting", "mwi"]
        }, [])
        assert r[0] == "webex_voicemail"
        assert "greeting" in r[1]

    def test_no_data_defaults(self):
        r = recommend_voicemail_incompatible({}, [])
        assert r[0] == "webex_voicemail"
        assert "default" in r[1].lower()


class TestForwardingLossy:
    def test_always_recommends_accept_loss(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_forwarding_lossy
        context = {"lossy_variants": ["callForwardBusyInt", "callForwardNoCoverage"]}
        options = [{"id": "accept"}, {"id": "manual"}, {"id": "skip"}]
        result = recommend_forwarding_lossy(context, options)
        assert result is not None
        assert result[0] == "accept"
        assert "CUCM-only" in result[1]


class TestSnrLossy:
    def test_always_recommends_accept_loss(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_snr_lossy
        context = {"cucm_answer_too_soon": 3000}
        options = [{"id": "accept"}, {"id": "skip"}, {"id": "manual"}]
        result = recommend_snr_lossy(context, options)
        assert result is not None
        assert result[0] == "accept"
        assert "Timer" in result[1]


class TestAudioAssetManual:
    def test_announcement_recommends_accept(self):
        r = recommend_audio_asset_manual(
            {"usage": "AA_GREETING", "name": "MainGreeting"}, [])
        assert r is not None
        assert r[0] == "accept"
        assert "MainGreeting" in r[1]

    def test_moh_source_recommends_accept(self):
        r = recommend_audio_asset_manual(
            {"moh_source_name": "Corporate_Hold", "source_type": "moh"}, [])
        assert r is not None
        assert r[0] == "accept"
        assert "Corporate_Hold" in r[1]
        assert "TFTP" in r[1]

    def test_never_recommends_use_default(self):
        """Custom audio was intentional — never suggest using Webex default."""
        # Even low-location MOH should not get use_default
        r = recommend_audio_asset_manual(
            {"usage": "MOH", "location_count": 1, "name": "LobbyMusic"}, [])
        assert r is not None
        assert r[0] == "accept"
        assert r[0] != "use_default"

    def test_generic_audio_recommends_accept(self):
        r = recommend_audio_asset_manual({"name": "SomeAudio"}, [])
        assert r is not None
        assert r[0] == "accept"


class TestDECTNetworkDesign:
    def test_no_location_returns_none(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_network_design
        r = recommend_dect_network_design(
            {"location_name": None, "cucm_device_pool": "HQ-Pool", "total_handsets": 10},
            [{"id": "manual"}, {"id": "skip"}],
        )
        assert r is None

    def test_no_inventory_recommends_accept(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_network_design
        r = recommend_dect_network_design(
            {
                "location_name": "loc:hq",
                "base_stations_provided": False,
                "cucm_device_pool": "HQ-Pool",
                "total_handsets": 15,
                "zone_count": 1,
            },
            [{"id": "accept"}, {"id": "manual"}, {"id": "skip"}],
        )
        assert r is not None
        assert r[0] == "accept"
        assert "HQ-Pool" in r[1]
        assert "15" in r[1]

    def test_multiple_zones_same_location_recommends_accept(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_network_design
        r = recommend_dect_network_design(
            {
                "location_name": "loc:hq",
                "base_stations_provided": True,
                "cucm_device_pool": "HQ-Pool",
                "total_handsets": 20,
                "zone_count": 3,
            },
            [{"id": "accept"}, {"id": "manual"}, {"id": "skip"}],
        )
        assert r is not None
        assert r[0] == "accept"
        assert "3" in r[1]

    def test_no_accept_option_returns_none(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_network_design
        r = recommend_dect_network_design(
            {
                "location_name": "loc:hq",
                "base_stations_provided": False,
                "cucm_device_pool": "HQ-Pool",
                "total_handsets": 5,
                "zone_count": 1,
            },
            [{"id": "manual"}, {"id": "skip"}],
        )
        assert r is None


class TestDECTHandsetAssignment:
    def test_unowned_handset_recommends_accept(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_handset_assignment
        r = recommend_dect_handset_assignment(
            {
                "owner_status": "unowned",
                "cucm_device_name": "DECT-Lobby-1",
                "network_canonical_id": "dect_network:net1",
            },
            [{"id": "accept"}, {"id": "manual"}, {"id": "skip"}],
        )
        assert r is not None
        assert r[0] == "accept"
        assert "DECT-Lobby-1" in r[1]

    def test_no_accept_option_returns_none(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_handset_assignment
        r = recommend_dect_handset_assignment(
            {"owner_status": "unowned", "cucm_device_name": "DECT-Office-2"},
            [{"id": "manual"}, {"id": "skip"}],
        )
        assert r is None

    def test_unknown_owner_status_returns_none(self):
        from wxcli.migration.advisory.recommendation_rules import recommend_dect_handset_assignment
        r = recommend_dect_handset_assignment(
            {"owner_status": "assigned", "cucm_device_name": "DECT-X"},
            [{"id": "accept"}, {"id": "skip"}],
        )
        assert r is None

    def test_dispatch_table_contains_dect_types(self):
        from wxcli.migration.advisory.recommendation_rules import RECOMMENDATION_DISPATCH
        assert "DECT_NETWORK_DESIGN" in RECOMMENDATION_DISPATCH
        assert "DECT_HANDSET_ASSIGNMENT" in RECOMMENDATION_DISPATCH
