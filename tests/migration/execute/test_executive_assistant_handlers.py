"""Tests for executive/assistant execution handlers and planner expansion.

Covers all 7 operation types from spec §4e:
  1. executive_type_assign
  2. assistant_type_assign
  3. executive_assign_assistants
  4. executive_configure_alert
  5. executive_configure_filtering
  6. executive_configure_screening
  7. assistant_configure_settings

Also covers planner expander _expand_executive_assistant().
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from wxcli.migration.execute import API_CALL_ESTIMATES, TIER_ASSIGNMENTS
from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    SkippedResult,
    handle_assistant_configure_settings,
    handle_assistant_type_assign,
    handle_executive_assign_assistants,
    handle_executive_configure_alert,
    handle_executive_configure_filtering,
    handle_executive_configure_screening,
    handle_executive_type_assign,
)
from wxcli.migration.execute.planner import expand_to_operations
from wxcli.migration.models import (
    CanonicalExecutiveAssistant,
    MigrationStatus,
    Provenance,
)
from wxcli.migration.store import MigrationStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    s = MigrationStore(tmp_path / "test.db")
    yield s
    s.close()


def _prov():
    return Provenance(
        source_system="cucm",
        source_id="pk-test",
        source_name="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _analyzed_ea(**kwargs) -> CanonicalExecutiveAssistant:
    defaults = {
        "canonical_id": "executive_assistant:jsmith",
        "status": MigrationStatus.ANALYZED,
        "provenance": _prov(),
        "executive_canonical_id": "user:jsmith@example.com",
        "assistant_canonical_ids": ["user:jdoe@example.com"],
        "alerting_mode": "SIMULTANEOUS",
        "filter_enabled": False,
        "filter_type": "ALL_CALLS",
        "screening_enabled": False,
    }
    defaults.update(kwargs)
    return CanonicalExecutiveAssistant(**defaults)


CTX = {"orgId": "org-123"}
DEPS = {
    "user:jsmith@example.com": "exec-webex-id",
    "user:jdoe@example.com": "asst-webex-id",
    "user:alice@example.com": "asst-webex-id-alice",
}


# ---------------------------------------------------------------------------
# Handler: handle_executive_type_assign
# ---------------------------------------------------------------------------

class TestHandleExecutiveTypeAssign:

    def test_produces_put_executive_type(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_executive_type_assign(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/people/exec-webex-id/features/executiveAssistant" in url
        assert body == {"type": "EXECUTIVE"}

    def test_injects_org_id(self):
        data = {"executive_canonical_id": "user:jsmith@example.com"}
        result = handle_executive_type_assign(data, DEPS, CTX)

        _, url, _ = result[0]
        assert "orgId=org-123" in url

    def test_skipped_when_executive_not_resolved(self):
        """Wave 2C: missing-dep returns SkippedResult, not []."""
        data = {"executive_canonical_id": "user:missing@example.com"}
        result = handle_executive_type_assign(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "not resolved" in result.reason

    def test_skipped_when_no_executive_canonical_id(self):
        """Wave 2C: no exec canonical_id at all also means unresolved."""
        data = {}
        result = handle_executive_type_assign(data, DEPS, CTX)
        assert isinstance(result, SkippedResult)


# ---------------------------------------------------------------------------
# Handler: handle_assistant_type_assign
# ---------------------------------------------------------------------------

class TestHandleAssistantTypeAssign:

    def test_produces_put_for_each_assistant(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": [
                "user:jdoe@example.com",
                "user:alice@example.com",
            ],
        }
        result = handle_assistant_type_assign(data, DEPS, CTX)

        assert len(result) == 2
        for method, url, body in result:
            assert method == "PUT"
            assert "/features/executiveAssistant" in url
            assert body == {"type": "EXECUTIVE_ASSISTANT"}

    def test_puts_correct_person_ids(self):
        data = {
            "assistant_canonical_ids": ["user:jdoe@example.com", "user:alice@example.com"],
        }
        result = handle_assistant_type_assign(data, DEPS, CTX)

        person_ids = [url.split("/people/")[1].split("/")[0] for _, url, _ in result]
        assert "asst-webex-id" in person_ids
        assert "asst-webex-id-alice" in person_ids

    def test_all_unresolved_assistants_returns_skipped(self):
        """Wave 2C: if assistant_cids were specified but NONE resolved,
        this is a missing-dep scenario (upstream user creates failed) —
        surface as SkippedResult rather than silent []."""
        data = {"assistant_canonical_ids": ["user:gone@example.com"]}
        result = handle_assistant_type_assign(data, DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "resolved" in result.reason

    def test_no_op_when_no_assistants(self):
        """Empty assistant_cids list = true no-op (nothing to configure)."""
        data = {"assistant_canonical_ids": []}
        result = handle_assistant_type_assign(data, DEPS, CTX)
        assert result == []

    def test_partial_resolution(self):
        """Resolved assistants produce calls; unresolved are skipped."""
        data = {
            "assistant_canonical_ids": [
                "user:jdoe@example.com",
                "user:gone@example.com",
            ],
        }
        result = handle_assistant_type_assign(data, DEPS, CTX)
        assert len(result) == 1
        _, url, _ = result[0]
        assert "asst-webex-id" in url


# ---------------------------------------------------------------------------
# Handler: handle_executive_assign_assistants
# ---------------------------------------------------------------------------

class TestHandleExecutiveAssignAssistants:

    def test_produces_put_assigned_assistants(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_executive_assign_assistants(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/exec-webex-id/executive/assignedAssistants" in url
        assert body["allowOptInEnabled"] is True
        assert len(body["assistants"]) == 1
        assert body["assistants"][0]["id"] == "asst-webex-id"
        assert body["assistants"][0]["optInEnabled"] is True

    def test_multiple_assistants(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": [
                "user:jdoe@example.com",
                "user:alice@example.com",
            ],
        }
        result = handle_executive_assign_assistants(data, DEPS, CTX)

        assert len(result) == 1
        _, _, body = result[0]
        assert len(body["assistants"]) == 2

    def test_skipped_when_executive_not_resolved(self):
        """Wave 2C: missing exec webex_id returns SkippedResult."""
        data = {
            "executive_canonical_id": "user:missing@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_executive_assign_assistants(data, {}, CTX)
        assert isinstance(result, SkippedResult)
        assert "not resolved" in result.reason

    def test_skipped_when_no_assistants_resolved(self):
        """Wave 2C: if assistants were expected but NONE resolved, skipped."""
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:gone@example.com"],
        }
        result = handle_executive_assign_assistants(data, DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "resolved" in result.reason

    def test_skips_unresolved_assistants_in_body(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": [
                "user:jdoe@example.com",
                "user:gone@example.com",
            ],
        }
        result = handle_executive_assign_assistants(data, DEPS, CTX)

        assert len(result) == 1
        _, _, body = result[0]
        assert len(body["assistants"]) == 1


# ---------------------------------------------------------------------------
# Handler: handle_executive_configure_alert
# ---------------------------------------------------------------------------

class TestHandleExecutiveConfigureAlert:

    def test_produces_put_alert_settings(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "alerting_mode": "SEQUENTIAL",
        }
        result = handle_executive_configure_alert(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/exec-webex-id/executive/alert" in url
        assert body["alertingMode"] == "SEQUENTIAL"

    def test_simultaneous_alerting_mode(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "alerting_mode": "SIMULTANEOUS",
        }
        result = handle_executive_configure_alert(data, DEPS, CTX)

        _, _, body = result[0]
        assert body["alertingMode"] == "SIMULTANEOUS"

    def test_includes_required_fields(self):
        data = {"executive_canonical_id": "user:jsmith@example.com"}
        result = handle_executive_configure_alert(data, DEPS, CTX)

        _, _, body = result[0]
        assert "nextAssistantNumberOfRings" in body
        assert "rolloverEnabled" in body
        assert "clidNameMode" in body
        assert "clidPhoneNumberMode" in body

    def test_skipped_when_executive_not_resolved(self):
        """Wave 2C: missing exec webex_id returns SkippedResult."""
        data = {"executive_canonical_id": "user:missing@example.com"}
        result = handle_executive_configure_alert(data, {}, CTX)
        assert isinstance(result, SkippedResult)


# ---------------------------------------------------------------------------
# Handler: handle_executive_configure_filtering
# ---------------------------------------------------------------------------

class TestHandleExecutiveConfigureFiltering:

    def test_produces_put_filtering(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "filter_enabled": True,
            "filter_type": "ALL_CALLS",
        }
        result = handle_executive_configure_filtering(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/exec-webex-id/executive/callFiltering" in url
        assert body["enabled"] is True
        assert body["filterType"] == "ALL_CALLS"

    def test_no_op_when_filter_disabled(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "filter_enabled": False,
        }
        result = handle_executive_configure_filtering(data, DEPS, CTX)
        assert result == []

    def test_maps_internal_only_filter_type(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "filter_enabled": True,
            "filter_type": "INTERNAL_ONLY",
        }
        result = handle_executive_configure_filtering(data, DEPS, CTX)

        _, _, body = result[0]
        assert body["filterType"] == "ALL_INTERNAL_CALLS"

    def test_maps_external_only_filter_type(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "filter_enabled": True,
            "filter_type": "EXTERNAL_ONLY",
        }
        result = handle_executive_configure_filtering(data, DEPS, CTX)

        _, _, body = result[0]
        assert body["filterType"] == "ALL_EXTERNAL_CALLS"

    def test_unknown_filter_type_defaults_to_all_calls(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "filter_enabled": True,
            "filter_type": "UNKNOWN_TYPE",
        }
        result = handle_executive_configure_filtering(data, DEPS, CTX)

        _, _, body = result[0]
        assert body["filterType"] == "ALL_CALLS"

    def test_skipped_when_executive_not_resolved(self):
        """Wave 2C: missing exec webex_id returns SkippedResult."""
        data = {
            "executive_canonical_id": "user:missing@example.com",
            "filter_enabled": True,
        }
        result = handle_executive_configure_filtering(data, {}, CTX)
        assert isinstance(result, SkippedResult)


# ---------------------------------------------------------------------------
# Handler: handle_executive_configure_screening
# ---------------------------------------------------------------------------

class TestHandleExecutiveConfigureScreening:

    def test_produces_put_screening(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "screening_enabled": True,
        }
        result = handle_executive_configure_screening(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/exec-webex-id/executive/screening" in url
        assert body["enabled"] is True
        assert body["alertType"] == "RING_SPLASH"

    def test_no_op_when_screening_disabled(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "screening_enabled": False,
        }
        result = handle_executive_configure_screening(data, DEPS, CTX)
        assert result == []

    def test_skipped_when_executive_not_resolved(self):
        """Wave 2C: missing exec webex_id returns SkippedResult."""
        data = {
            "executive_canonical_id": "user:missing@example.com",
            "screening_enabled": True,
        }
        result = handle_executive_configure_screening(data, {}, CTX)
        assert isinstance(result, SkippedResult)


# ---------------------------------------------------------------------------
# Handler: handle_assistant_configure_settings
# ---------------------------------------------------------------------------

class TestHandleAssistantConfigureSettings:

    def test_produces_put_for_each_assistant(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)

        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/people/asst-webex-id/executive/assistant" in url
        assert body["forwardFilteredCallsEnabled"] is False

    def test_includes_executive_in_body_when_resolved(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)

        _, _, body = result[0]
        assert "executives" in body
        assert len(body["executives"]) == 1
        assert body["executives"][0]["personId"] == "exec-webex-id"
        assert body["executives"][0]["optInEnabled"] is True

    def test_multiple_assistants(self):
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": [
                "user:jdoe@example.com",
                "user:alice@example.com",
            ],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)
        assert len(result) == 2

    def test_skipped_when_all_assistants_unresolved(self):
        """Wave 2C: if assistant_cids specified but NONE resolved, skipped."""
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": ["user:gone@example.com"],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)
        assert isinstance(result, SkippedResult)
        assert "resolved" in result.reason

    def test_no_op_when_no_assistants(self):
        """Empty assistant_cids list = true no-op."""
        data = {
            "executive_canonical_id": "user:jsmith@example.com",
            "assistant_canonical_ids": [],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)
        assert result == []

    def test_no_executive_in_body_when_unresolved(self):
        """When the executive is not resolved, the body still sends but without executives list."""
        data = {
            "executive_canonical_id": "user:missing@example.com",
            "assistant_canonical_ids": ["user:jdoe@example.com"],
        }
        result = handle_assistant_configure_settings(data, DEPS, CTX)
        assert len(result) == 1
        _, _, body = result[0]
        assert "executives" not in body or body.get("executives") is None


# ---------------------------------------------------------------------------
# Handler registry validation
# ---------------------------------------------------------------------------

class TestHandlerRegistryEntries:

    def test_all_seven_ops_in_registry(self):
        expected = [
            ("executive_assistant", "assign_executive_type"),
            ("executive_assistant", "assign_assistant_type"),
            ("executive_assistant", "assign_assistants"),
            ("executive_assistant", "configure_alert"),
            ("executive_assistant", "configure_filtering"),
            ("executive_assistant", "configure_screening"),
            ("executive_assistant", "configure_assistant_settings"),
        ]
        for key in expected:
            assert key in HANDLER_REGISTRY, f"Missing from HANDLER_REGISTRY: {key}"

    def test_all_seven_ops_in_tier_assignments(self):
        expected = [
            ("executive_assistant", "assign_executive_type"),
            ("executive_assistant", "assign_assistant_type"),
            ("executive_assistant", "assign_assistants"),
            ("executive_assistant", "configure_alert"),
            ("executive_assistant", "configure_filtering"),
            ("executive_assistant", "configure_screening"),
            ("executive_assistant", "configure_assistant_settings"),
        ]
        for key in expected:
            assert key in TIER_ASSIGNMENTS, f"Missing from TIER_ASSIGNMENTS: {key}"
            assert TIER_ASSIGNMENTS[key] == 5, f"Expected tier 5 for {key}"

    def test_all_seven_ops_in_api_call_estimates(self):
        expected = [
            "executive_assistant:assign_executive_type",
            "executive_assistant:assign_assistant_type",
            "executive_assistant:assign_assistants",
            "executive_assistant:configure_alert",
            "executive_assistant:configure_filtering",
            "executive_assistant:configure_screening",
            "executive_assistant:configure_assistant_settings",
        ]
        for key in expected:
            assert key in API_CALL_ESTIMATES, f"Missing from API_CALL_ESTIMATES: {key}"


# ---------------------------------------------------------------------------
# Planner expander tests
# ---------------------------------------------------------------------------

class TestExpandExecutiveAssistantPlanner:

    def test_basic_pair_produces_all_ops(self, store):
        ea = _analyzed_ea(
            filter_enabled=True,
            screening_enabled=True,
        )
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        op_types = {o.op_type for o in ea_ops}
        assert "assign_executive_type" in op_types
        assert "assign_assistant_type" in op_types
        assert "assign_assistants" in op_types
        assert "configure_alert" in op_types
        assert "configure_filtering" in op_types
        assert "configure_screening" in op_types
        assert "configure_assistant_settings" in op_types

    def test_no_filtering_op_when_filter_disabled(self, store):
        ea = _analyzed_ea(filter_enabled=False, screening_enabled=False)
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        op_types = {o.op_type for o in ea_ops}
        assert "configure_filtering" not in op_types

    def test_no_screening_op_when_screening_disabled(self, store):
        ea = _analyzed_ea(filter_enabled=False, screening_enabled=False)
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        op_types = {o.op_type for o in ea_ops}
        assert "configure_screening" not in op_types

    def test_all_ops_at_tier_5(self, store):
        ea = _analyzed_ea(filter_enabled=True, screening_enabled=True)
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        assert all(o.tier == 5 for o in ea_ops), (
            "All executive_assistant ops should be tier 5"
        )

    def test_assign_assistants_depends_on_both_type_assignments(self, store):
        ea = _analyzed_ea()
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        assign_op = next(
            (o for o in ea_ops if o.op_type == "assign_assistants"), None
        )
        assert assign_op is not None

        cid = ea.canonical_id
        assert f"{cid}:assign_executive_type" in assign_op.depends_on
        assert f"{cid}:assign_assistant_type" in assign_op.depends_on

    def test_post_pairing_ops_depend_on_assign_assistants(self, store):
        ea = _analyzed_ea(filter_enabled=True, screening_enabled=True)
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        cid = ea.canonical_id
        assign_node = f"{cid}:assign_assistants"

        post_types = {
            "configure_alert",
            "configure_filtering",
            "configure_screening",
            "configure_assistant_settings",
        }
        for op in ea_ops:
            if op.op_type in post_types:
                assert assign_node in op.depends_on, (
                    f"{op.op_type} should depend on assign_assistants"
                )

    def test_type_assign_depends_on_user_create(self, store):
        ea = _analyzed_ea()
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        exec_type_op = next(
            (o for o in ea_ops if o.op_type == "assign_executive_type"), None
        )
        assert exec_type_op is not None
        assert "user:jsmith@example.com:create" in exec_type_op.depends_on

    def test_no_ops_when_no_executive_or_assistants(self, store):
        ea = _analyzed_ea(
            executive_canonical_id=None,
            assistant_canonical_ids=[],
        )
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]
        assert ea_ops == []

    def test_multi_assistant_pair(self, store):
        ea = _analyzed_ea(
            assistant_canonical_ids=[
                "user:jdoe@example.com",
                "user:alice@example.com",
                "user:bob@example.com",
            ]
        )
        store.upsert_object(ea)

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]

        asst_type_op = next(
            (o for o in ea_ops if o.op_type == "assign_assistant_type"), None
        )
        assert asst_type_op is not None
        # All three assistants should be in depends_on
        assert "user:jdoe@example.com:create" in asst_type_op.depends_on
        assert "user:alice@example.com:create" in asst_type_op.depends_on
        assert "user:bob@example.com:create" in asst_type_op.depends_on

    def test_skipped_object_produces_no_ops(self, store):
        """MISSING_DATA decision with skip suppresses all ops."""
        ea = _analyzed_ea()
        store.upsert_object(ea)
        store.save_decision({
            "decision_id": "D0001",
            "type": "MISSING_DATA",
            "severity": "HIGH",
            "summary": "Broken exec/assistant pairing",
            "context": {"_affected_objects": [ea.canonical_id]},
            "options": [{"id": "skip", "label": "Skip", "impact": "none"}],
            "chosen_option": "skip",
            "resolved_at": "2026-01-01T00:00:00Z",
            "resolved_by": "user",
            "fingerprint": "fp-ea-missing",
            "run_id": "test-run",
        })

        ops = expand_to_operations(store)
        ea_ops = [o for o in ops if o.resource_type == "executive_assistant"]
        assert ea_ops == []
