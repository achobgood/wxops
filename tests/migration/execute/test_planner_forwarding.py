"""Tests for planner expansion of HG/CQ/AA configure_* operations."""
from __future__ import annotations

from wxcli.migration.execute.planner import (
    _expand_auto_attendant,
    _expand_call_queue,
    _expand_hunt_group,
)


def _op_types(ops) -> list[str]:
    return [op.op_type for op in ops]


class TestHuntGroupExpansion:
    def test_no_forwarding_no_extra_ops(self):
        obj = {
            "canonical_id": "hunt_group:abc",
            "name": "HG1",
            "agents": [],
            "location_id": "location:loc1",
        }
        ops = _expand_hunt_group(obj)
        assert _op_types(ops) == ["create"]

    def test_with_no_answer_forwarding_emits_configure(self):
        obj = {
            "canonical_id": "hunt_group:abc",
            "name": "HG1",
            "agents": [],
            "location_id": "location:loc1",
            "forward_no_answer_enabled": True,
            "forward_no_answer_destination": "5999",
        }
        ops = _expand_hunt_group(obj)
        assert _op_types(ops) == ["create", "configure_forwarding"]
        configure = ops[1]
        assert configure.tier == 5
        assert configure.depends_on == ["hunt_group:abc:create"]

    def test_with_busy_forwarding_emits_configure(self):
        obj = {
            "canonical_id": "hunt_group:abc",
            "name": "HG1",
            "agents": [],
            "location_id": "location:loc1",
            "forward_busy_enabled": True,
            "forward_busy_destination": "5199",
        }
        ops = _expand_hunt_group(obj)
        assert _op_types(ops) == ["create", "configure_forwarding"]


class TestCallQueueExpansion:
    def _base(self) -> dict:
        return {
            "canonical_id": "call_queue:abc",
            "name": "CQ1",
            "agents": [],
            "location_id": "location:loc1",
        }

    def test_minimal_emits_only_create(self):
        ops = _expand_call_queue(self._base())
        assert _op_types(ops) == ["create"]

    def test_overflow_emits_configure_forwarding(self):
        obj = self._base()
        obj["queue_full_destination"] = "+15555550100"
        ops = _expand_call_queue(obj)
        assert "configure_forwarding" in _op_types(ops)

    def test_holiday_emits_configure_holiday(self):
        obj = self._base()
        obj["holiday_service_enabled"] = True
        obj["holiday_schedule_name"] = "2026 Holidays"
        ops = _expand_call_queue(obj)
        assert "configure_holiday_service" in _op_types(ops)

    def test_night_emits_configure_night(self):
        obj = self._base()
        obj["night_service_enabled"] = True
        obj["night_business_hours_name"] = "Working Hours"
        ops = _expand_call_queue(obj)
        assert "configure_night_service" in _op_types(ops)

    def test_stranded_emits_configure_stranded(self):
        obj = self._base()
        obj["no_agent_destination"] = "+15555559000"
        ops = _expand_call_queue(obj)
        assert "configure_stranded_calls" in _op_types(ops)

    def test_all_settings_emit_all_ops(self):
        obj = self._base()
        obj.update({
            "queue_full_destination": "+15555550100",
            "holiday_service_enabled": True,
            "holiday_schedule_name": "2026 Holidays",
            "night_service_enabled": True,
            "night_business_hours_name": "Working Hours",
            "no_agent_destination": "+15555559000",
        })
        ops = _expand_call_queue(obj)
        names = _op_types(ops)
        assert names == [
            "create",
            "configure_forwarding",
            "configure_holiday_service",
            "configure_night_service",
            "configure_stranded_calls",
        ]
        # All configure ops depend on the create op
        for op in ops[1:]:
            assert op.depends_on == ["call_queue:abc:create"]
            assert op.tier == 5


class TestAutoAttendantExpansion:
    def test_no_forwarding_no_extra_ops(self):
        obj = {
            "canonical_id": "auto_attendant:abc",
            "name": "AA1",
            "location_id": "location:loc1",
        }
        ops = _expand_auto_attendant(obj)
        assert _op_types(ops) == ["create"]

    def test_forward_always_emits_configure(self):
        obj = {
            "canonical_id": "auto_attendant:abc",
            "name": "AA1",
            "location_id": "location:loc1",
            "forward_always_enabled": True,
            "forward_always_destination": "+15555559999",
        }
        ops = _expand_auto_attendant(obj)
        assert _op_types(ops) == ["create", "configure_forwarding"]
        assert ops[1].tier == 5
        assert ops[1].depends_on == ["auto_attendant:abc:create"]
