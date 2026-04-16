"""Tests for HG/CQ/AA configure_* handlers."""
from __future__ import annotations

import pytest


CTX = {"orgId": "ORG123"}


def _hg_data(**overrides):
    base = {
        "canonical_id": "hunt_group:abc",
        "location_id": "location:loc1",
        "forward_always_enabled": False,
        "forward_always_destination": None,
        "forward_busy_enabled": False,
        "forward_busy_destination": None,
        "forward_no_answer_enabled": False,
        "forward_no_answer_destination": None,
    }
    base.update(overrides)
    return base


def _cq_data(**overrides):
    base = {
        "canonical_id": "call_queue:abc",
        "location_id": "location:loc1",
        "forward_always_enabled": False,
        "forward_always_destination": None,
        "queue_full_destination": None,
        "max_wait_time_destination": None,
        "no_agent_destination": None,
        "holiday_service_enabled": False,
        "holiday_schedule_name": None,
        "holiday_schedule_level": "LOCATION",
        "holiday_action": "BUSY",
        "holiday_transfer_number": None,
        "night_service_enabled": False,
        "night_business_hours_name": None,
        "night_business_hours_level": "LOCATION",
        "night_action": "TRANSFER",
        "night_transfer_number": None,
    }
    base.update(overrides)
    return base


def _aa_data(**overrides):
    base = {
        "canonical_id": "auto_attendant:abc",
        "location_id": "location:loc1",
        "forward_always_enabled": False,
        "forward_always_destination": None,
    }
    base.update(overrides)
    return base


def _deps(feature_cid: str) -> dict:
    return {
        "location:loc1": "WEBEX_LOC_1",
        feature_cid: "WEBEX_FEATURE_1",
    }


class TestHuntGroupConfigureForwarding:
    def test_no_forwarding_returns_empty(self):
        from wxcli.migration.execute.handlers import (
            handle_hunt_group_configure_forwarding,
        )
        result = handle_hunt_group_configure_forwarding(
            _hg_data(), _deps("hunt_group:abc"), CTX,
        )
        assert result == []

    def test_missing_webex_id_returns_skipped(self):
        """Wave 2C: missing hunt_group webex_id now returns SkippedResult,
        not [] — so the op lands in status='skipped' and cascade-skips
        dependents instead of silently looking completed."""
        from wxcli.migration.execute.handlers import (
            SkippedResult,
            handle_hunt_group_configure_forwarding,
        )
        data = _hg_data(forward_always_enabled=True,
                       forward_always_destination="5999")
        # No Webex ID for the feature
        deps = {"location:loc1": "WEBEX_LOC_1"}
        result = handle_hunt_group_configure_forwarding(data, deps, CTX)
        assert isinstance(result, SkippedResult)
        assert "not created" in result.reason

    def test_always_forwarding_builds_put(self):
        from wxcli.migration.execute.handlers import (
            handle_hunt_group_configure_forwarding,
        )
        data = _hg_data(
            forward_always_enabled=True,
            forward_always_destination="5999",
        )
        result = handle_hunt_group_configure_forwarding(
            data, _deps("hunt_group:abc"), CTX,
        )
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/huntGroups/WEBEX_FEATURE_1/callForwarding" in url
        assert "orgId=ORG123" in url
        assert body["callForwarding"]["always"]["enabled"] is True
        assert body["callForwarding"]["always"]["destination"] == "5999"

    def test_no_answer_uses_selective_block(self):
        from wxcli.migration.execute.handlers import (
            handle_hunt_group_configure_forwarding,
        )
        data = _hg_data(
            forward_no_answer_enabled=True,
            forward_no_answer_destination="5111",
        )
        result = handle_hunt_group_configure_forwarding(
            data, _deps("hunt_group:abc"), CTX,
        )
        method, url, body = result[0]
        assert body["callForwarding"]["selective"]["enabled"] is True
        assert body["callForwarding"]["selective"]["destination"] == "5111"


class TestCallQueueConfigureForwarding:
    def test_no_forwarding_returns_empty(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_forwarding,
        )
        result = handle_call_queue_configure_forwarding(
            _cq_data(), _deps("call_queue:abc"), CTX,
        )
        assert result == []

    def test_queue_full_destination_maps_to_always(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_forwarding,
        )
        data = _cq_data(queue_full_destination="+15555550100")
        result = handle_call_queue_configure_forwarding(
            data, _deps("call_queue:abc"), CTX,
        )
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/queues/WEBEX_FEATURE_1/callForwarding" in url
        assert body["callForwarding"]["always"]["destination"] == "+15555550100"


class TestCallQueueConfigureHolidayService:
    def test_emits_put_with_schedule_and_action(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_holiday_service,
        )
        data = _cq_data(
            holiday_service_enabled=True,
            holiday_schedule_name="2026 Holidays",
            holiday_schedule_level="LOCATION",
            holiday_action="TRANSFER",
            holiday_transfer_number="+15555559000",
        )
        result = handle_call_queue_configure_holiday_service(
            data, _deps("call_queue:abc"), CTX,
        )
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/queues/WEBEX_FEATURE_1/holidayService" in url
        assert body["holidayServiceEnabled"] is True
        assert body["holidayScheduleName"] == "2026 Holidays"
        assert body["holidayScheduleLevel"] == "LOCATION"
        assert body["action"] == "TRANSFER"
        assert body["transferPhoneNumber"] == "+15555559000"

    def test_busy_action_omits_transfer_number(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_holiday_service,
        )
        data = _cq_data(
            holiday_service_enabled=True,
            holiday_schedule_name="2026 Holidays",
            holiday_action="BUSY",
        )
        result = handle_call_queue_configure_holiday_service(
            data, _deps("call_queue:abc"), CTX,
        )
        method, url, body = result[0]
        assert body["action"] == "BUSY"
        assert "transferPhoneNumber" not in body


class TestCallQueueConfigureNightService:
    def test_emits_put_with_business_hours(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_night_service,
        )
        data = _cq_data(
            night_service_enabled=True,
            night_business_hours_name="Working Hours",
            night_business_hours_level="LOCATION",
            night_transfer_number="+15555558000",
        )
        result = handle_call_queue_configure_night_service(
            data, _deps("call_queue:abc"), CTX,
        )
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/queues/WEBEX_FEATURE_1/nightService" in url
        assert body["nightServiceEnabled"] is True
        assert body["businessHoursName"] == "Working Hours"
        assert body["businessHoursLevel"] == "LOCATION"
        assert body["action"] == "TRANSFER"
        assert body["transferPhoneNumber"] == "+15555558000"


class TestCallQueueConfigureStrandedCalls:
    def test_emits_put_with_transfer_number(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_stranded_calls,
        )
        data = _cq_data(no_agent_destination="+15555557000")
        result = handle_call_queue_configure_stranded_calls(
            data, _deps("call_queue:abc"), CTX,
        )
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/queues/WEBEX_FEATURE_1/strandedCalls" in url
        assert body["action"] == "TRANSFER"
        assert body["transferPhoneNumber"] == "+15555557000"

    def test_missing_destination_returns_empty(self):
        from wxcli.migration.execute.handlers import (
            handle_call_queue_configure_stranded_calls,
        )
        result = handle_call_queue_configure_stranded_calls(
            _cq_data(), _deps("call_queue:abc"), CTX,
        )
        assert result == []


class TestAutoAttendantConfigureForwarding:
    def test_no_forwarding_returns_empty(self):
        from wxcli.migration.execute.handlers import (
            handle_auto_attendant_configure_forwarding,
        )
        result = handle_auto_attendant_configure_forwarding(
            _aa_data(), _deps("auto_attendant:abc"), CTX,
        )
        assert result == []

    def test_always_forwarding_emits_put(self):
        from wxcli.migration.execute.handlers import (
            handle_auto_attendant_configure_forwarding,
        )
        data = _aa_data(
            forward_always_enabled=True,
            forward_always_destination="+15555559999",
        )
        result = handle_auto_attendant_configure_forwarding(
            data, _deps("auto_attendant:abc"), CTX,
        )
        method, url, body = result[0]
        assert method == "PUT"
        assert "/locations/WEBEX_LOC_1/autoAttendants/WEBEX_FEATURE_1/callForwarding" in url
        assert body["callForwarding"]["always"]["enabled"] is True
        assert body["callForwarding"]["always"]["destination"] == "+15555559999"
