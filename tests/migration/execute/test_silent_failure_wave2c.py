"""Wave 2C of silent-failure-hardening — handlers.py lines 1320-end.

Scope: converts guard-clause ``return []`` sites to ``return skipped(...)`` for
the 22 handlers owned by Wave 2C. Covers two regression properties per site:

1. **Missing-dep → ``SkippedResult``**: when a required upstream webex_id or
   location can't be resolved, the handler MUST return ``SkippedResult`` so the
   engine records the op as ``status='skipped'`` (cascade-skip dependents,
   surface in the execution report, avoid silent "completed" on zero work).

2. **Dep present → list of tuples**: when all deps resolve, the handler STILL
   returns the normal ``[(method, url, body), ...]`` list — the conversion did
   not break the happy path.

Plus an explicit regression guard: ``handle_music_on_hold_configure`` and
``handle_announcement_upload`` are deliberate Phase A placeholder no-ops per
``src/wxcli/migration/execute/CLAUDE.md``. They MUST remain ``return []`` —
Wave 2C did NOT convert them because the plan entry is cosmetic (there is no
real API call yet). This test locks in that intent so a future "sweep the
rest" commit doesn't accidentally convert them and start cascade-skipping
downstream ops that have no actual dependency on MOH/announcement work.

Handlers covered (22 total):
  - handle_hunt_group_configure_forwarding
  - handle_call_queue_configure_forwarding
  - handle_call_queue_configure_holiday_service
  - handle_call_queue_configure_night_service
  - handle_call_queue_configure_stranded_calls
  - handle_auto_attendant_configure_forwarding
  - handle_bulk_device_settings_submit
  - handle_bulk_line_key_template_submit
  - handle_bulk_dynamic_settings_submit
  - handle_bulk_rebuild_phones_submit
  - handle_music_on_hold_configure          (no-op placeholder — KEEP [])
  - handle_announcement_upload              (no-op placeholder — KEEP [])
  - handle_executive_type_assign
  - handle_assistant_type_assign
  - handle_executive_assign_assistants
  - handle_executive_configure_alert
  - handle_executive_configure_filtering
  - handle_executive_configure_screening
  - handle_assistant_configure_settings
  - handle_dect_network_create
  - handle_dect_base_station_create
  - handle_dect_handset_assign
"""

from __future__ import annotations

import pytest

from wxcli.migration.execute.handlers import (
    SkippedResult,
    handle_announcement_upload,
    handle_assistant_configure_settings,
    handle_assistant_type_assign,
    handle_auto_attendant_configure_forwarding,
    handle_bulk_device_settings_submit,
    handle_bulk_dynamic_settings_submit,
    handle_bulk_line_key_template_submit,
    handle_bulk_rebuild_phones_submit,
    handle_call_queue_configure_forwarding,
    handle_call_queue_configure_holiday_service,
    handle_call_queue_configure_night_service,
    handle_call_queue_configure_stranded_calls,
    handle_dect_base_station_create,
    handle_dect_handset_assign,
    handle_dect_network_create,
    handle_executive_assign_assistants,
    handle_executive_configure_alert,
    handle_executive_configure_filtering,
    handle_executive_configure_screening,
    handle_executive_type_assign,
    handle_hunt_group_configure_forwarding,
    handle_music_on_hold_configure,
)

CTX = {"orgId": "ORG-XYZ"}


# ---------------------------------------------------------------------------
# hunt_group / call_queue / auto_attendant configure_forwarding family
# ---------------------------------------------------------------------------

class TestHuntGroupConfigureForwarding:
    """Missing hunt_group webex_id or location → SkippedResult.
    Both present + forwarding configured → PUT call.
    """

    DATA = {
        "canonical_id": "hunt_group:hg-abc",
        "name": "Sales Hunt",
        "location_id": "location:loc-1",
        "forward_always_enabled": True,
        "forward_always_destination": "5999",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        # hg webex_id not in deps — upstream hunt_group:create failed/skipped
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_hunt_group_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "not created" in result.reason
        assert "Sales Hunt" in result.reason

    def test_missing_location_webex_id_returns_skipped(self):
        deps = {"hunt_group:hg-abc": "WEBEX_HG_1"}
        result = handle_hunt_group_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "location not resolved" in result.reason

    def test_deps_present_returns_put_list(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "hunt_group:hg-abc": "WEBEX_HG_1",
        }
        result = handle_hunt_group_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/huntGroups/WEBEX_HG_1/callForwarding" in url
        assert body["callForwarding"]["always"]["destination"] == "5999"


class TestCallQueueConfigureForwarding:
    DATA = {
        "canonical_id": "call_queue:cq-abc",
        "name": "Support Queue",
        "location_id": "location:loc-1",
        "queue_full_destination": "+15555550100",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_call_queue_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "Support Queue" in result.reason

    def test_missing_location_returns_skipped(self):
        deps = {"call_queue:cq-abc": "WEBEX_CQ_1"}
        result = handle_call_queue_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "location not resolved" in result.reason

    def test_deps_present_returns_put(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "call_queue:cq-abc": "WEBEX_CQ_1",
        }
        result = handle_call_queue_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert result[0][0] == "PUT"


class TestCallQueueConfigureHolidayService:
    DATA = {
        "canonical_id": "call_queue:cq-abc",
        "name": "Support Queue",
        "location_id": "location:loc-1",
        "holiday_service_enabled": True,
        "holiday_schedule_name": "Holidays 2026",
        "holiday_schedule_level": "LOCATION",
        "holiday_action": "BUSY",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_call_queue_configure_holiday_service(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "holiday service" in result.reason

    def test_missing_location_returns_skipped(self):
        deps = {"call_queue:cq-abc": "WEBEX_CQ_1"}
        result = handle_call_queue_configure_holiday_service(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "location not resolved" in result.reason

    def test_deps_present_returns_put(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "call_queue:cq-abc": "WEBEX_CQ_1",
        }
        result = handle_call_queue_configure_holiday_service(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert result[0][0] == "PUT"


class TestCallQueueConfigureNightService:
    DATA = {
        "canonical_id": "call_queue:cq-abc",
        "name": "Support Queue",
        "location_id": "location:loc-1",
        "night_service_enabled": True,
        "night_business_hours_name": "Business Hours",
        "night_transfer_number": "+15555550200",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_call_queue_configure_night_service(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "night service" in result.reason

    def test_missing_location_returns_skipped(self):
        deps = {"call_queue:cq-abc": "WEBEX_CQ_1"}
        result = handle_call_queue_configure_night_service(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)

    def test_deps_present_returns_put(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "call_queue:cq-abc": "WEBEX_CQ_1",
        }
        result = handle_call_queue_configure_night_service(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert result[0][0] == "PUT"


class TestCallQueueConfigureStrandedCalls:
    DATA = {
        "canonical_id": "call_queue:cq-abc",
        "name": "Support Queue",
        "location_id": "location:loc-1",
        "no_agent_destination": "+15555550300",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_call_queue_configure_stranded_calls(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "stranded calls" in result.reason

    def test_missing_location_returns_skipped(self):
        deps = {"call_queue:cq-abc": "WEBEX_CQ_1"}
        result = handle_call_queue_configure_stranded_calls(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)

    def test_deps_present_returns_put(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "call_queue:cq-abc": "WEBEX_CQ_1",
        }
        result = handle_call_queue_configure_stranded_calls(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert result[0][0] == "PUT"


class TestAutoAttendantConfigureForwarding:
    DATA = {
        "canonical_id": "auto_attendant:aa-abc",
        "name": "Main AA",
        "location_id": "location:loc-1",
        "forward_always_enabled": True,
        "forward_always_destination": "+15555559999",
    }

    def test_missing_feature_webex_id_returns_skipped(self):
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_auto_attendant_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "auto attendant" in result.reason
        assert "Main AA" in result.reason

    def test_missing_location_returns_skipped(self):
        deps = {"auto_attendant:aa-abc": "WEBEX_AA_1"}
        result = handle_auto_attendant_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "location not resolved" in result.reason

    def test_deps_present_returns_put(self):
        deps = {
            "location:loc-1": "WEBEX_LOC_1",
            "auto_attendant:aa-abc": "WEBEX_AA_1",
        }
        result = handle_auto_attendant_configure_forwarding(self.DATA, deps, CTX)
        assert isinstance(result, list)
        assert result[0][0] == "PUT"


# ---------------------------------------------------------------------------
# Bulk job submit handlers
# ---------------------------------------------------------------------------

class TestBulkDeviceSettingsSubmit:

    def test_missing_location_returns_skipped(self):
        data = {"location_canonical_id": "location:loc-1", "customizations": {}}
        result = handle_bulk_device_settings_submit(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "location" in result.reason

    def test_deps_present_returns_post(self):
        data = {"location_canonical_id": "location:loc-1", "customizations": {"foo": "bar"}}
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_bulk_device_settings_submit(data, deps, CTX)
        assert isinstance(result, list)
        method, url, body = result[0]
        assert method == "POST"
        assert body["locationId"] == "WEBEX_LOC_1"


class TestBulkLineKeyTemplateSubmit:

    def test_missing_template_webex_id_returns_skipped(self):
        data = {
            "template_canonical_id": "line_key_template:tpl-1",
            "location_canonical_ids": ["location:loc-1"],
        }
        deps = {"location:loc-1": "WEBEX_LOC_1"}  # template not resolved
        result = handle_bulk_line_key_template_submit(data, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "line key template" in result.reason

    def test_deps_present_returns_post(self):
        data = {
            "template_canonical_id": "line_key_template:tpl-1",
            "location_canonical_ids": ["location:loc-1"],
        }
        deps = {
            "line_key_template:tpl-1": "WEBEX_TPL_1",
            "location:loc-1": "WEBEX_LOC_1",
        }
        result = handle_bulk_line_key_template_submit(data, deps, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body["templateId"] == "WEBEX_TPL_1"
        assert body["locationIds"] == ["WEBEX_LOC_1"]


class TestBulkDynamicSettingsSubmit:

    def test_missing_location_returns_skipped(self):
        data = {"location_canonical_id": "location:loc-1", "tags": []}
        result = handle_bulk_dynamic_settings_submit(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "not resolved" in result.reason

    def test_deps_present_returns_post(self):
        data = {
            "location_canonical_id": "location:loc-1",
            "tags": [{"tag": "%FOO%", "action": "CLEAR"}],
        }
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_bulk_dynamic_settings_submit(data, deps, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body["locationId"] == "WEBEX_LOC_1"


class TestBulkRebuildPhonesSubmit:

    def test_missing_location_returns_skipped(self):
        data = {"location_canonical_id": "location:loc-1"}
        result = handle_bulk_rebuild_phones_submit(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "location" in result.reason

    def test_deps_present_returns_post(self):
        data = {"location_canonical_id": "location:loc-1"}
        deps = {"location:loc-1": "WEBEX_LOC_1"}
        result = handle_bulk_rebuild_phones_submit(data, deps, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body == {"locationId": "WEBEX_LOC_1"}


# ---------------------------------------------------------------------------
# MOH + announcement — deliberate Phase A no-op placeholders.
# These MUST stay `return []` per execute/CLAUDE.md. This test locks in
# the intent so a future "sweep the rest" commit doesn't accidentally
# convert them and start cascade-skipping unrelated downstream work.
# ---------------------------------------------------------------------------

class TestMohAnnouncementPlaceholderRegressionGuard:

    def test_music_on_hold_configure_still_returns_empty(self):
        """Phase A visibility placeholder — Phase B adds real PUT + multipart.
        Until then the op exists in the plan for operator visibility only."""
        result = handle_music_on_hold_configure({}, {}, CTX)
        assert result == []

    def test_music_on_hold_configure_empty_regardless_of_data(self):
        # Even with every possible dep resolved, MOH:configure is a no-op
        # in Phase A. Don't start treating it as a missing-dep site.
        data = {"location_canonical_id": "location:loc-1", "canonical_id": "moh:loc-1"}
        deps = {"location:loc-1": "WEBEX_LOC_1", "moh:loc-1": "WEBEX_MOH_1"}
        result = handle_music_on_hold_configure(data, deps, CTX)
        assert result == []

    def test_announcement_upload_still_returns_empty(self):
        """Phase A visibility placeholder — Phase B adds multipart upload."""
        result = handle_announcement_upload({}, {}, CTX)
        assert result == []

    def test_announcement_upload_empty_regardless_of_data(self):
        data = {"canonical_id": "announcement:abc", "audio_asset": "foo.wav"}
        deps = {"announcement:abc": "WEBEX_AUDIO_1"}
        result = handle_announcement_upload(data, deps, CTX)
        assert result == []


# ---------------------------------------------------------------------------
# Executive / assistant handlers
# ---------------------------------------------------------------------------

EXEC_DEPS = {
    "user:exec@ex.com": "WEBEX_EXEC",
    "user:asst1@ex.com": "WEBEX_ASST1",
    "user:asst2@ex.com": "WEBEX_ASST2",
}


class TestExecutiveTypeAssign:

    def test_missing_exec_returns_skipped(self):
        data = {"executive_canonical_id": "user:gone@ex.com"}
        result = handle_executive_type_assign(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "executive user" in result.reason

    def test_no_exec_canonical_id_returns_skipped(self):
        result = handle_executive_type_assign({}, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_deps_present_returns_put(self):
        data = {"executive_canonical_id": "user:exec@ex.com"}
        result = handle_executive_type_assign(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        method, url, body = result[0]
        assert method == "PUT"
        assert "WEBEX_EXEC" in url
        assert body == {"type": "EXECUTIVE"}


class TestAssistantTypeAssign:

    def test_empty_assistants_is_true_no_op(self):
        """Zero assistant_cids = nothing to do, correctly returns []."""
        data = {"assistant_canonical_ids": []}
        result = handle_assistant_type_assign(data, EXEC_DEPS, CTX)
        assert result == []

    def test_all_unresolved_returns_skipped(self):
        """assistant_cids specified but NONE resolved → missing-dep."""
        data = {"assistant_canonical_ids": ["user:gone1@ex.com", "user:gone2@ex.com"]}
        result = handle_assistant_type_assign(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "resolved" in result.reason

    def test_partial_resolution_returns_puts(self):
        """Some resolved + some unresolved = still emit ops for resolved ones.
        This matches the partial-membership semantics from spec resolved
        decision #3 (HG/CQ partial membership)."""
        data = {
            "assistant_canonical_ids": ["user:asst1@ex.com", "user:gone@ex.com"],
        }
        result = handle_assistant_type_assign(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        assert len(result) == 1
        _, url, _ = result[0]
        assert "WEBEX_ASST1" in url

    def test_all_resolved_returns_puts(self):
        data = {
            "assistant_canonical_ids": ["user:asst1@ex.com", "user:asst2@ex.com"],
        }
        result = handle_assistant_type_assign(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        assert len(result) == 2


class TestExecutiveAssignAssistants:

    def test_missing_exec_returns_skipped(self):
        data = {
            "executive_canonical_id": "user:gone@ex.com",
            "assistant_canonical_ids": ["user:asst1@ex.com"],
        }
        result = handle_executive_assign_assistants(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "executive user" in result.reason

    def test_all_assistants_unresolved_returns_skipped(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": ["user:gone@ex.com"],
        }
        result = handle_executive_assign_assistants(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_empty_assistants_is_no_op(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": [],
        }
        result = handle_executive_assign_assistants(data, EXEC_DEPS, CTX)
        assert result == []

    def test_deps_present_returns_put(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": ["user:asst1@ex.com"],
        }
        result = handle_executive_assign_assistants(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        method, url, body = result[0]
        assert method == "PUT"
        assert "WEBEX_EXEC" in url
        assert body["assistants"][0]["id"] == "WEBEX_ASST1"


class TestExecutiveConfigureAlert:

    def test_missing_exec_returns_skipped(self):
        data = {"executive_canonical_id": "user:gone@ex.com"}
        result = handle_executive_configure_alert(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_deps_present_returns_put(self):
        data = {"executive_canonical_id": "user:exec@ex.com", "alerting_mode": "SIMULTANEOUS"}
        result = handle_executive_configure_alert(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        _, url, body = result[0]
        assert "WEBEX_EXEC" in url
        assert body["alertingMode"] == "SIMULTANEOUS"


class TestExecutiveConfigureFiltering:

    def test_missing_exec_returns_skipped(self):
        data = {"executive_canonical_id": "user:gone@ex.com", "filter_enabled": True}
        result = handle_executive_configure_filtering(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_filter_disabled_is_true_no_op(self):
        """filter_enabled=False = nothing to configure → []."""
        data = {"executive_canonical_id": "user:exec@ex.com", "filter_enabled": False}
        result = handle_executive_configure_filtering(data, EXEC_DEPS, CTX)
        assert result == []

    def test_deps_present_returns_put(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "filter_enabled": True,
            "filter_type": "ALL_CALLS",
        }
        result = handle_executive_configure_filtering(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body["enabled"] is True


class TestExecutiveConfigureScreening:

    def test_missing_exec_returns_skipped(self):
        data = {"executive_canonical_id": "user:gone@ex.com", "screening_enabled": True}
        result = handle_executive_configure_screening(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_screening_disabled_is_true_no_op(self):
        data = {"executive_canonical_id": "user:exec@ex.com", "screening_enabled": False}
        result = handle_executive_configure_screening(data, EXEC_DEPS, CTX)
        assert result == []

    def test_deps_present_returns_put(self):
        data = {"executive_canonical_id": "user:exec@ex.com", "screening_enabled": True}
        result = handle_executive_configure_screening(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body["enabled"] is True


class TestAssistantConfigureSettings:

    def test_empty_assistants_is_no_op(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": [],
        }
        result = handle_assistant_configure_settings(data, EXEC_DEPS, CTX)
        assert result == []

    def test_all_assistants_unresolved_returns_skipped(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": ["user:gone@ex.com"],
        }
        result = handle_assistant_configure_settings(data, EXEC_DEPS, CTX)
        assert isinstance(result, SkippedResult)

    def test_partial_resolution_returns_puts(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": ["user:asst1@ex.com", "user:gone@ex.com"],
        }
        result = handle_assistant_configure_settings(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_deps_present_returns_puts(self):
        data = {
            "executive_canonical_id": "user:exec@ex.com",
            "assistant_canonical_ids": ["user:asst1@ex.com"],
        }
        result = handle_assistant_configure_settings(data, EXEC_DEPS, CTX)
        assert isinstance(result, list)
        _, _, body = result[0]
        assert body["forwardFilteredCallsEnabled"] is False
        assert body["executives"][0]["personId"] == "WEBEX_EXEC"


# ---------------------------------------------------------------------------
# DECT handlers
# ---------------------------------------------------------------------------

DECT_LOC_CID = "location:loc-dect"
DECT_NET_CID = "dect_network:warehouse-dect"


class TestDectNetworkCreate:

    DATA = {
        "canonical_id": DECT_NET_CID,
        "location_id": DECT_LOC_CID,
        "network_name": "Warehouse-DECT",
        "display_name": "Warehouse DECT",
        "model": "DBS-210",
        "access_code": "1234",
    }

    def test_missing_location_returns_skipped(self):
        data = {**self.DATA, "location_id": None, "location_canonical_id": None}
        result = handle_dect_network_create(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "location" in result.reason

    def test_missing_name_is_true_no_op(self):
        """Missing name = data-integrity issue, not missing-dep. Still a []."""
        data = {**self.DATA, "network_name": None, "display_name": None}
        result = handle_dect_network_create(data, {DECT_LOC_CID: "WID"}, CTX)
        assert result == []

    def test_deps_present_returns_post(self):
        result = handle_dect_network_create(self.DATA, {DECT_LOC_CID: "WID"}, CTX)
        assert isinstance(result, list)
        method, url, body = result[0]
        assert method == "POST"
        assert "/dectNetworks" in url
        assert body["name"] == "Warehouse-DECT"


class TestDectBaseStationCreate:

    DATA = {
        "canonical_id": DECT_NET_CID,
        "location_id": DECT_LOC_CID,
        "base_stations": [{"mac": "AABBCCDDEEFF"}],
    }

    def test_missing_location_returns_skipped(self):
        data = {**self.DATA, "location_id": None, "location_canonical_id": None}
        result = handle_dect_base_station_create(data, {DECT_NET_CID: "NET_WID"}, CTX)
        assert isinstance(result, SkippedResult)

    def test_missing_network_webex_id_returns_skipped(self):
        """DECT network:create hasn't completed → network wid absent → skipped."""
        result = handle_dect_base_station_create(self.DATA, {DECT_LOC_CID: "LOC_WID"}, CTX)
        assert isinstance(result, SkippedResult)
        assert "DECT network" in result.reason

    def test_no_base_stations_is_true_no_op(self):
        """Empty base_stations list = true no-op per spec."""
        data = {**self.DATA, "base_stations": []}
        deps = {DECT_LOC_CID: "LOC_WID", DECT_NET_CID: "NET_WID"}
        result = handle_dect_base_station_create(data, deps, CTX)
        assert result == []

    def test_deps_present_returns_post(self):
        deps = {DECT_LOC_CID: "LOC_WID", DECT_NET_CID: "NET_WID"}
        result = handle_dect_base_station_create(self.DATA, deps, CTX)
        assert isinstance(result, list)
        method, url, body = result[0]
        assert method == "POST"
        assert "/baseStations" in url
        assert body["baseStationMacs"] == ["AABBCCDDEEFF"]


class TestDectHandsetAssign:

    DATA = {
        "canonical_id": DECT_NET_CID,
        "location_id": DECT_LOC_CID,
        "handset_assignments": [
            {
                "user_canonical_id": "user:jsmith@ex.com",
                "display_name": "John Smith",
                "line1_canonical_id": "user:jsmith@ex.com",
                "line2_canonical_id": None,
            },
        ],
    }

    def test_missing_location_returns_skipped(self):
        data = {**self.DATA, "location_id": None, "location_canonical_id": None}
        deps = {DECT_NET_CID: "NET_WID"}
        result = handle_dect_handset_assign(data, deps, CTX)
        assert isinstance(result, SkippedResult)

    def test_missing_network_webex_id_returns_skipped(self):
        deps = {DECT_LOC_CID: "LOC_WID"}
        result = handle_dect_handset_assign(self.DATA, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "DECT network" in result.reason

    def test_no_handsets_is_true_no_op(self):
        """Empty handset_assignments = true no-op per spec."""
        data = {**self.DATA, "handset_assignments": []}
        deps = {DECT_LOC_CID: "LOC_WID", DECT_NET_CID: "NET_WID"}
        result = handle_dect_handset_assign(data, deps, CTX)
        assert result == []

    def test_deps_present_returns_post(self):
        deps = {
            DECT_LOC_CID: "LOC_WID",
            DECT_NET_CID: "NET_WID",
            "user:jsmith@ex.com": "WEBEX_JSMITH",
        }
        result = handle_dect_handset_assign(self.DATA, deps, CTX)
        assert isinstance(result, list)
        _, url, body = result[0]
        assert "/handsets/bulk" in url
        assert body["items"][0]["line1MemberId"] == "WEBEX_JSMITH"
