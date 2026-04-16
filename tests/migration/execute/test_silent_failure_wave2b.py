"""Wave 2B silent-failure-hardening tests for handlers.py lines 770-1320.

For every guard-clause site converted from ``return []`` to
``return skipped(...)``, this file asserts:

* Missing-dep guard returns ``SkippedResult`` with a useful reason.
* Present-dep case returns a non-empty list of ``(method, url, body)`` tuples
  (or an empty list when the legitimate "nothing to configure" path is hit).

Issue #16 (monitoring list) and issue #17 (shared line) have extra
partial-vs-full-drop coverage per the hardening spec.
"""
from __future__ import annotations

import logging

import pytest

from wxcli.migration.execute.handlers import (
    SkippedResult,
    handle_call_forwarding_configure,
    handle_device_configure_settings,
    handle_device_layout_configure,
    handle_device_settings_template_apply_device_override,
    handle_device_settings_template_apply_location_settings,
    handle_ecbn_config_configure,
    handle_hoteling_guest_enable,
    handle_hoteling_host_configure,
    handle_location_hotdesking_enable,
    handle_monitoring_list_configure,
    handle_receptionist_config_configure,
    handle_shared_line_configure,
    handle_snr_configure,
    handle_softkey_config_configure,
    handle_virtual_line_configure,
    handle_workspace_configure_settings,
)


# ---------------------------------------------------------------------------
# ecbn_config:configure
# ---------------------------------------------------------------------------


class TestEcbnConfigConfigure:
    def test_missing_entity_dep_skipped(self):
        data = {
            "entity_type": "user",
            "entity_canonical_id": "user:alice@example.com",
            "ecbn_selection": "DIRECT_LINE",
        }
        result = handle_ecbn_config_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:alice@example.com" in result.reason

    def test_unknown_entity_type_skipped(self):
        data = {
            "entity_type": "bogus",
            "entity_canonical_id": "bogus:xxx",
            "ecbn_selection": "DIRECT_LINE",
        }
        deps = {"bogus:xxx": "wx-123"}
        result = handle_ecbn_config_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "bogus" in result.reason

    def test_missing_location_member_skipped(self):
        data = {
            "entity_type": "user",
            "entity_canonical_id": "user:alice@example.com",
            "ecbn_selection": "LOCATION_MEMBER_NUMBER",
            "location_member_canonical_id": "user:bob@example.com",
        }
        deps = {"user:alice@example.com": "wx-alice"}
        result = handle_ecbn_config_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "user:bob@example.com" in result.reason

    def test_resolved_returns_put(self):
        data = {
            "entity_type": "user",
            "entity_canonical_id": "user:alice@example.com",
            "ecbn_selection": "DIRECT_LINE",
        }
        deps = {"user:alice@example.com": "wx-alice"}
        result = handle_ecbn_config_configure(data, deps, {})
        assert isinstance(result, list)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-alice" in url
        assert body == {"selected": "DIRECT_LINE"}


# ---------------------------------------------------------------------------
# device:configure_settings
# ---------------------------------------------------------------------------


class TestDeviceConfigureSettings:
    def test_missing_device_skipped(self):
        data = {"device_settings": {"allowThirdPartyControl": True}}
        result = handle_device_configure_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device" in result.reason

    def test_resolved_returns_put(self):
        data = {"device_settings": {"allowThirdPartyControl": True}}
        deps = {"device:d1": "wx-dev-111"}
        result = handle_device_configure_settings(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


# ---------------------------------------------------------------------------
# workspace:configure_settings
# ---------------------------------------------------------------------------


class TestWorkspaceConfigureSettings:
    def test_missing_workspace_skipped(self):
        data = {"call_settings": {"doNotDisturb": {"enabled": True}}}
        result = handle_workspace_configure_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "workspace" in result.reason

    def test_resolved_returns_put(self):
        data = {"call_settings": {"doNotDisturb": {"enabled": True}}}
        deps = {"workspace:w1": "wx-ws-xyz"}
        result = handle_workspace_configure_settings(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


# ---------------------------------------------------------------------------
# call_forwarding:configure
# ---------------------------------------------------------------------------


class TestCallForwardingConfigure:
    def test_missing_user_skipped(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": True,
            "always_destination": "+15551234567",
        }
        result = handle_call_forwarding_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jsmith" in result.reason

    def test_resolved_returns_put(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "always_enabled": True,
            "always_destination": "+15551234567",
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_call_forwarding_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


# ---------------------------------------------------------------------------
# single_number_reach:configure
# ---------------------------------------------------------------------------


class TestSnrConfigure:
    def test_missing_user_skipped(self):
        data = {"user_canonical_id": "user:jdoe", "numbers": [{"phone_number": "+1"}]}
        result = handle_snr_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jdoe" in result.reason

    def test_resolved_returns_calls(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "enabled": True,
            "numbers": [{"phone_number": "+15551230000", "enabled": True}],
        }
        deps = {"user:jdoe": "wx-person-jdoe"}
        result = handle_snr_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 2  # PUT + POST


# ---------------------------------------------------------------------------
# monitoring_list:configure (issue #16)
# ---------------------------------------------------------------------------


class TestMonitoringListConfigure:
    def test_missing_user_skipped(self):
        data = {
            "user_canonical_id": "user:jsmith",
            "monitored_members": [{"target_canonical_id": "user:alice"}],
        }
        result = handle_monitoring_list_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jsmith" in result.reason

    def test_all_members_unresolved_skipped(self):
        """Issue #16: if every member fails to resolve, return skipped."""
        data = {
            "name": "Sales Monitors",
            "user_canonical_id": "user:jsmith",
            "monitored_members": [
                {"target_canonical_id": "user:gone1"},
                {"target_canonical_id": "user:gone2"},
            ],
        }
        deps = {"user:jsmith": "wx-person-aaa"}
        result = handle_monitoring_list_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "Sales Monitors" in result.reason
        assert "2" in result.reason

    def test_partial_drop_returns_list_and_warns(self, caplog):
        """Issue #16: some-resolved-some-unresolved → PUT with warning logged."""
        data = {
            "user_canonical_id": "user:jsmith",
            "monitored_members": [
                {"target_canonical_id": "user:alice"},
                {"target_canonical_id": "user:bob_missing"},
                {"target_canonical_id": "user:carol"},
            ],
        }
        deps = {
            "user:jsmith": "wx-person-aaa",
            "user:alice": "wx-alice",
            "user:carol": "wx-carol",
        }
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.handlers"):
            result = handle_monitoring_list_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 1
        _, _, body = result[0]
        assert len(body["monitoredMembers"]) == 2
        # Warning must mention unresolved member
        assert any("user:bob_missing" in rec.getMessage() for rec in caplog.records)

    def test_all_resolved_returns_put_no_warning(self, caplog):
        data = {
            "user_canonical_id": "user:jsmith",
            "monitored_members": [{"target_canonical_id": "user:alice"}],
        }
        deps = {"user:jsmith": "wx-person-aaa", "user:alice": "wx-alice"}
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.handlers"):
            result = handle_monitoring_list_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 1
        # No unresolved-member warning when everything resolves.
        assert not any(
            "unresolved" in rec.getMessage() for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# receptionist_config:configure
# ---------------------------------------------------------------------------


class TestReceptionistConfigConfigure:
    def test_missing_user_skipped(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "monitored_members": [],
            "location_canonical_id": "location:HQ",
        }
        result = handle_receptionist_config_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jdoe" in result.reason

    def test_resolved_returns_calls(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "monitored_members": ["user:alice"],
            "location_canonical_id": "location:HQ",
        }
        deps = {
            "user:jdoe": "wx-jdoe",
            "user:alice": "wx-alice",
            "location:HQ": "wx-loc-hq",
        }
        result = handle_receptionist_config_configure(data, deps, {})
        assert isinstance(result, list) and len(result) >= 1


# ---------------------------------------------------------------------------
# device_layout:configure
# ---------------------------------------------------------------------------


class TestDeviceLayoutConfigure:
    def test_missing_device_skipped(self):
        data = {
            "device_canonical_id": "device:SEPAAA",
            "line_members": [],
            "resolved_line_keys": [],
            "resolved_kem_keys": [],
        }
        result = handle_device_layout_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device:SEPAAA" in result.reason

    def test_resolved_returns_calls(self):
        data = {
            "device_canonical_id": "device:SEPAAA",
            "line_members": [],
            "resolved_line_keys": [],
            "resolved_kem_keys": [],
        }
        deps = {"device:SEPAAA": "wx-dev-aaa"}
        result = handle_device_layout_configure(data, deps, {})
        # At minimum: PUT layout + POST applyChanges
        assert isinstance(result, list) and len(result) >= 2


# ---------------------------------------------------------------------------
# softkey_config:configure
# ---------------------------------------------------------------------------


class TestSoftkeyConfigConfigure:
    def test_missing_device_skipped(self):
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001",
            "psk_mappings": [{"psk_slot": "PSK1", "keyword": "park"}],
            "state_key_lists": {},
        }
        result = handle_softkey_config_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device:SEP001" in result.reason

    def test_resolved_returns_calls(self):
        data = {
            "is_psk_target": True,
            "device_canonical_id": "device:SEP001",
            "psk_mappings": [{"psk_slot": "PSK1", "keyword": "park"}],
            "state_key_lists": {},
        }
        deps = {"device:SEP001": "wx-dev-001"}
        result = handle_softkey_config_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 2


# ---------------------------------------------------------------------------
# shared_line:configure (issue #17)
# ---------------------------------------------------------------------------


class TestSharedLineConfigureIssue17:
    def test_zero_resolved_owners_skipped(self):
        data = {
            "owner_canonical_ids": ["user:a", "user:b"],
            "device_canonical_ids": [],
        }
        result = handle_shared_line_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "0 of 2" in result.reason

    def test_one_resolved_owner_skipped(self):
        data = {
            "owner_canonical_ids": ["user:a", "user:b"],
            "device_canonical_ids": [],
        }
        deps = {"user:a": "wx-a"}
        result = handle_shared_line_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "1 of 2" in result.reason

    def test_two_resolved_owners_returns_puts(self):
        data = {
            "owner_canonical_ids": ["user:a", "user:b"],
            "device_canonical_ids": [],
        }
        deps = {"user:a": "wx-a", "user:b": "wx-b"}
        result = handle_shared_line_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 2
        for method, url, _ in result:
            assert method == "PUT"
            assert "applications/members" in url


# ---------------------------------------------------------------------------
# virtual_line:configure
# ---------------------------------------------------------------------------


class TestVirtualLineConfigure:
    def test_missing_vl_skipped(self):
        data = {
            "display_name": "Sales VL",
            "canonical_id": "virtual_line:sales",
            "settings": {"callerIdName": "VL"},
        }
        result = handle_virtual_line_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        # Either display_name or canonical_id should appear for operator context
        assert "Sales VL" in result.reason or "virtual_line:sales" in result.reason

    def test_resolved_returns_put(self):
        data = {"settings": {"callerIdName": "VL"}}
        deps = {"virtual_line:vl1": "wx-vl-aaa"}
        result = handle_virtual_line_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


# ---------------------------------------------------------------------------
# device_settings_template — apply_location_settings / apply_device_override
# ---------------------------------------------------------------------------


class TestDeviceSettingsTemplateApplyLocationSettings:
    def test_no_location_cid_skipped(self):
        data = {"settings": {"bluetooth": {"enabled": True}}}
        result = handle_device_settings_template_apply_location_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "location_canonical_id" in result.reason

    def test_no_location_dep_skipped(self):
        data = {
            "location_canonical_id": "location:HQ",
            "settings": {"bluetooth": {"enabled": True}},
        }
        result = handle_device_settings_template_apply_location_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "location:HQ" in result.reason

    def test_resolved_returns_put(self):
        data = {
            "location_canonical_id": "location:HQ",
            "settings": {"bluetooth": {"enabled": True}},
        }
        deps = {"location:HQ": "wx-loc-abc"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


class TestDeviceSettingsTemplateApplyDeviceOverride:
    def test_no_device_cid_skipped(self):
        data = {}
        result = handle_device_settings_template_apply_device_override(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device_canonical_id" in result.reason

    def test_no_device_dep_skipped(self):
        data = {
            "override": {
                "device_canonical_id": "device:MISSING",
                "settings": {"bluetooth": {"enabled": False}},
            },
        }
        result = handle_device_settings_template_apply_device_override(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device:MISSING" in result.reason

    def test_resolved_returns_put(self):
        data = {
            "override": {
                "device_canonical_id": "device:SEP001",
                "settings": {"bluetooth": {"enabled": False}},
            },
        }
        deps = {"device:SEP001": "wx-dev-001"}
        result = handle_device_settings_template_apply_device_override(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


# ---------------------------------------------------------------------------
# hoteling_guest_enable / hoteling_host_configure / location_hotdesking_enable
# ---------------------------------------------------------------------------


class TestHotelingGuestEnable:
    def test_missing_user_skipped(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "hoteling_guest_enabled": True,
        }
        result = handle_hoteling_guest_enable(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jdoe" in result.reason

    def test_resolved_returns_put(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "hoteling_guest_enabled": True,
        }
        deps = {"user:jdoe": "wx-jdoe"}
        result = handle_hoteling_guest_enable(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


class TestHotelingHostConfigure:
    def test_missing_user_skipped(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "host_device_canonical_ids": ["device:d1"],
        }
        result = handle_hoteling_host_configure(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "user:jdoe" in result.reason

    def test_no_host_device_resolved_skipped(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "host_device_canonical_ids": ["device:d1", "device:d2"],
        }
        deps = {"user:jdoe": "wx-jdoe"}  # devices NOT resolved
        result = handle_hoteling_host_configure(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "host device" in result.reason.lower()

    def test_partial_host_device_resolved_returns_put(self):
        data = {
            "user_canonical_id": "user:jdoe",
            "host_device_canonical_ids": ["device:d1", "device:d2"],
        }
        deps = {"user:jdoe": "wx-jdoe", "device:d1": "wx-d1"}
        result = handle_hoteling_host_configure(data, deps, {})
        assert isinstance(result, list) and len(result) == 1


class TestLocationHotdeskingEnable:
    def test_missing_location_skipped(self):
        data = {"pre_migration_state": {"location_canonical_id": "location:Unknown"}}
        result = handle_location_hotdesking_enable(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "location:Unknown" in result.reason

    def test_resolved_returns_put(self):
        data = {"pre_migration_state": {"location_canonical_id": "location:HQ"}}
        deps = {"location:HQ": "wx-loc-hq"}
        result = handle_location_hotdesking_enable(data, deps, {})
        assert isinstance(result, list) and len(result) == 1
