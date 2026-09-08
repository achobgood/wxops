"""Tests for wxcli cleanup command."""
import pytest
from unittest.mock import MagicMock
from wxcli.errors import WebexError


def _make_webex_error(message: str = "not found", status_code: int = 404) -> WebexError:
    return WebexError(message)


def test_resource_registry_has_all_types():
    """Every resource type in DELETION_LAYERS exists in RESOURCE_TYPES."""
    from wxcli.commands.cleanup import DELETION_LAYERS, RESOURCE_TYPES

    all_keys_in_layers = []
    for layer in DELETION_LAYERS:
        all_keys_in_layers.extend(layer)

    for key in all_keys_in_layers:
        assert key in RESOURCE_TYPES, f"Missing registry entry for {key}"


def test_resource_registry_fields():
    """Each resource type has required fields."""
    from wxcli.commands.cleanup import RESOURCE_TYPES

    for key, rt in RESOURCE_TYPES.items():
        assert rt.name, f"{key} missing name"
        assert rt.list_url, f"{key} missing list_url"
        assert rt.delete_url, f"{key} missing delete_url"
        assert rt.item_key, f"{key} missing item_key"


def test_deletion_layers_order():
    """Layers are ordered: routing before features before infra."""
    from wxcli.commands.cleanup import DELETION_LAYERS

    assert len(DELETION_LAYERS) >= 12

    flat = []
    for i, layer in enumerate(DELETION_LAYERS):
        for key in layer:
            flat.append((key, i))
    pos = dict(flat)

    assert pos["dial_plans"] < pos["hunt_groups"]
    assert pos["trunks"] < pos["hunt_groups"]
    assert pos["hunt_groups"] < pos["virtual_lines"]
    assert pos["virtual_lines"] < pos["devices"]
    assert pos["devices"] < pos["workspaces"]
    assert pos["workspaces"] < pos["users"]
    assert pos["users"] < pos["locations"]


def test_location_scoped_resources_flagged():
    """Resources that need per-location listing are flagged."""
    from wxcli.commands.cleanup import RESOURCE_TYPES

    location_scoped = ["call_parks", "call_pickups", "schedules"]
    for key in location_scoped:
        assert RESOURCE_TYPES[key].location_scoped_list, (
            f"{key} should be location_scoped_list=True"
        )


def _make_api_mock():
    """Create a mock API with session.rest_get and follow_pagination."""
    api = MagicMock()
    api.session.rest_get.return_value = {}
    api.session.follow_pagination.return_value = iter([])
    return api


def test_list_resources_org_scoped():
    """list_resources for org-scoped type calls follow_pagination."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, list_resources

    api = _make_api_mock()
    api.session.follow_pagination.return_value = iter([
        {"id": "hg1", "name": "HG One", "locationId": "loc1"},
    ])

    items = list_resources(api, RESOURCE_TYPES["hunt_groups"], org_id=None, location_ids=None)
    assert len(items) == 1
    assert items[0]["id"] == "hg1"
    api.session.follow_pagination.assert_called_once()


def test_list_resources_location_scoped():
    """list_resources for location-scoped type iterates locations."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, list_resources

    api = _make_api_mock()
    api.session.follow_pagination.return_value = iter([
        {"id": "cp1", "name": "Park 1"},
    ])

    items = list_resources(api, RESOURCE_TYPES["call_parks"], org_id=None, location_ids=["loc1"])
    assert len(items) == 1
    assert items[0]["id"] == "cp1"
    call_args = api.session.follow_pagination.call_args
    assert "loc1" in call_args[1]["url"]


def test_list_resources_scope_filter():
    """list_resources with location_ids filters org-scoped results."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, list_resources

    api = _make_api_mock()
    api.session.follow_pagination.return_value = iter([
        {"id": "hg1", "name": "HG One", "locationId": "loc1"},
        {"id": "hg2", "name": "HG Two", "locationId": "loc2"},
    ])

    items = list_resources(
        api, RESOURCE_TYPES["hunt_groups"], org_id=None, location_ids=["loc1"],
    )
    assert len(items) == 1
    assert items[0]["id"] == "hg1"


def test_inventory_excludes_users_and_locations_by_default():
    """build_inventory skips users and locations when flags are False."""
    from wxcli.commands.cleanup import build_inventory

    api = _make_api_mock()
    api.session.follow_pagination.return_value = iter([
        {"id": "x1", "name": "X", "locationId": "l1"},
    ])

    result = build_inventory(
        api, org_id=None, location_ids=["l1"],
        include_users=False, include_locations=False,
    )
    assert "users" not in result
    assert "locations" not in result
    assert isinstance(result, dict)


def test_delete_resource_simple():
    """delete_resource calls rest_delete with correct URL."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, delete_resource

    api = _make_api_mock()
    item = {"id": "dp1", "name": "DP One"}
    result = delete_resource(api, RESOURCE_TYPES["dial_plans"], item, org_id=None)
    assert result.success is True
    assert result.resource_id == "dp1"
    api.session.rest_delete.assert_called_once()
    call_url = api.session.rest_delete.call_args[0][0]
    assert "dp1" in call_url


def test_delete_resource_location_scoped():
    """delete_resource for location-scoped type includes location_id in URL."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, delete_resource

    api = _make_api_mock()
    item = {"id": "hg1", "name": "HG One", "locationId": "loc1"}
    result = delete_resource(api, RESOURCE_TYPES["hunt_groups"], item, org_id=None)
    assert result.success is True
    call_url = api.session.rest_delete.call_args[0][0]
    assert "loc1" in call_url
    assert "hg1" in call_url


def test_delete_resource_schedule_needs_type():
    """delete_resource for schedules includes type in URL."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, delete_resource

    api = _make_api_mock()
    item = {"id": "sch1", "name": "Biz Hours", "type": "businessHours", "locationId": "loc1"}
    result = delete_resource(api, RESOURCE_TYPES["schedules"], item, org_id=None)
    assert result.success is True
    call_url = api.session.rest_delete.call_args[0][0]
    assert "businessHours" in call_url
    assert "sch1" in call_url


def test_delete_resource_error():
    """delete_resource returns failure on RestError."""
    from wxcli.commands.cleanup import RESOURCE_TYPES, delete_resource

    api = _make_api_mock()
    api.session.rest_delete.side_effect = _make_webex_error("not found")
    item = {"id": "dp1", "name": "DP One"}
    result = delete_resource(api, RESOURCE_TYPES["dial_plans"], item, org_id=None)
    assert result.success is False
    assert result.error is not None


def test_execute_layer_parallel():
    """execute_layer deletes all items and returns results."""
    from wxcli.commands.cleanup import execute_layer

    api = _make_api_mock()
    inventory = {
        "dial_plans": [
            {"id": "dp1", "name": "DP One"},
            {"id": "dp2", "name": "DP Two"},
        ],
    }
    results = execute_layer(
        api, ["dial_plans"], inventory, org_id=None, max_concurrent=2,
    )
    assert len(results) == 2
    assert all(r.success for r in results)


def test_disable_calling_on_location():
    """disable_location_calling sends DELETE to telephony config URL."""
    from wxcli.commands.cleanup import disable_location_calling

    api = _make_api_mock()
    result = disable_location_calling(api, "loc1", org_id=None)
    assert result.success is True
    call_url = api.session.rest_delete.call_args[0][0]
    assert "/telephony/config/locations/loc1" in call_url


def test_delete_location_after_disable():
    """delete_location sends DELETE to /locations/{id}."""
    from wxcli.commands.cleanup import delete_location

    api = _make_api_mock()
    result = delete_location(api, {"id": "loc1", "name": "HQ"}, org_id=None)
    assert result.success is True
    call_url = api.session.rest_delete.call_args[0][0]
    assert "/locations/loc1" in call_url
    assert "/telephony/" not in call_url


def test_format_dry_run_output():
    """format_dry_run produces a table with resource counts per layer."""
    from wxcli.commands.cleanup import format_dry_run

    inventory = {
        "dial_plans": [{"id": "dp1", "name": "DP1"}],
        "hunt_groups": [
            {"id": "hg1", "name": "HG1", "locationId": "l1"},
            {"id": "hg2", "name": "HG2", "locationId": "l1"},
        ],
    }
    output = format_dry_run(inventory)
    assert "Dial Plans" in output
    assert "1" in output
    assert "Hunt Groups" in output
    assert "2" in output


def test_format_results_summary():
    """format_results_summary shows success/failure counts."""
    from wxcli.commands.cleanup import DeleteResult, format_results_summary

    results = [
        DeleteResult("HG", "hg1", "HG1", success=True),
        DeleteResult("HG", "hg2", "HG2", success=True),
        DeleteResult("AA", "aa1", "AA1", success=False, error="409 conflict"),
    ]
    output = format_results_summary(results)
    assert "2" in output
    assert "1" in output
    assert "409" in output


# ---------------------------------------------------------------------------
# CCP-integrated PSTN backend gate
# ---------------------------------------------------------------------------

def test_is_ccp_integrated_error_by_code():
    """ERR.V.TRM.TMN60004 is recognized as the CCP signature."""
    from wxcli.commands.cleanup import _is_ccp_integrated_error

    msg = (
        '{"message":"DELETE number is supported only for non-integrated CCP",'
        '"errors":[{"code":"ERR.V.TRM.TMN60004"}]}'
    )
    assert _is_ccp_integrated_error(msg) is True


def test_is_ccp_integrated_error_by_message():
    """Message mentioning 'non-integrated CCP' also trips detection."""
    from wxcli.commands.cleanup import _is_ccp_integrated_error

    assert _is_ccp_integrated_error(
        "DELETE number is supported only for non-integrated CCP"
    ) is True


def test_is_ccp_integrated_error_empty_or_unrelated():
    """Unrelated errors are not CCP."""
    from wxcli.commands.cleanup import _is_ccp_integrated_error

    assert _is_ccp_integrated_error("") is False
    assert _is_ccp_integrated_error("not found") is False
    assert _is_ccp_integrated_error("409 conflict: being referenced") is False


def test_is_ccp_backend_gate_explicit_code():
    """Explicit CCP code always fires the gate regardless of local deps."""
    from wxcli.commands.cleanup import _is_ccp_backend_gate

    err = "ERR.V.TRM.TMN60004: cannot delete"
    assert _is_ccp_backend_gate(err, local_dependencies_clear=False) is True
    assert _is_ccp_backend_gate(err, local_dependencies_clear=True) is True


def test_is_ccp_backend_gate_being_referenced_requires_clear_deps():
    """Generic 'being referenced' is not sufficient to infer CCP."""
    from wxcli.commands.cleanup import _is_ccp_backend_gate

    err = "409 conflict: location is being referenced"
    assert _is_ccp_backend_gate(err, local_dependencies_clear=True) is False
    assert _is_ccp_backend_gate(err, local_dependencies_clear=False) is False


def test_delete_location_exits_retry_loop_on_ccp_code(monkeypatch):
    """delete_location short-circuits the retry loop on the CCP signature."""
    import wxcli.commands.cleanup as cleanup_mod
    from wxcli.commands.cleanup import delete_location

    # Fail the probe calls (treated as clear) so they don't mask the gate,
    # and ensure time.sleep is never hit — 5x60s would exceed test budget.
    sleeps: list[int] = []
    monkeypatch.setattr(cleanup_mod.time, "sleep", lambda s: sleeps.append(s))

    api = _make_api_mock()
    api.session.rest_delete.side_effect = _make_webex_error(
        "ERR.V.TRM.TMN60004 cannot delete trunk", status_code=409,
    )

    result = delete_location(
        api, {"id": "loc1", "name": "dCloud HQ"}, org_id=None,
    )
    assert result.success is False
    assert result.ccp_blocked is True
    assert "CCP-integrated PSTN backend" in (result.error or "")
    # Only one delete attempt — no retries.
    assert api.session.rest_delete.call_count == 1
    assert sleeps == []


def test_delete_location_being_referenced_with_clear_deps_retries(monkeypatch):
    """Generic 'being referenced' should stay on the normal retry path."""
    import wxcli.commands.cleanup as cleanup_mod
    from wxcli.commands.cleanup import delete_location

    sleeps: list[int] = []
    monkeypatch.setattr(cleanup_mod.time, "sleep", lambda s: sleeps.append(s))

    api = _make_api_mock()
    # No dependencies anywhere.
    api.session.rest_get.return_value = {}
    api.session.rest_delete.side_effect = _make_webex_error(
        "409: location is being referenced", status_code=409,
    )

    result = delete_location(
        api, {"id": "loc1", "name": "Branch"}, org_id=None,
        max_attempts=2, retry_sleep=0,
    )
    assert result.ccp_blocked is False
    assert result.success is False
    assert api.session.rest_delete.call_count == 2
    assert sleeps == [0]


def test_delete_location_being_referenced_with_deps_retries(monkeypatch):
    """'being referenced' + visible dependencies = normal retry path."""
    import wxcli.commands.cleanup as cleanup_mod
    from wxcli.commands.cleanup import delete_location

    sleeps: list[int] = []
    monkeypatch.setattr(cleanup_mod.time, "sleep", lambda s: sleeps.append(s))

    api = _make_api_mock()
    # Simulate lingering workspaces at the location.
    api.session.rest_get.return_value = {
        "items": [{"id": "ws1", "locationId": "loc1"}],
    }
    api.session.rest_delete.side_effect = _make_webex_error(
        "409: being referenced", status_code=409,
    )

    result = delete_location(
        api, {"id": "loc1", "name": "Branch"}, org_id=None,
        max_attempts=2, retry_sleep=0,
    )
    assert result.ccp_blocked is False
    assert result.success is False
    # Retried — attempted twice.
    assert api.session.rest_delete.call_count == 2


def test_location_blockers_detect_numbers_and_voice_portal():
    """Number inventory and voice portal state are surfaced as blockers."""
    from wxcli.commands.cleanup import _location_blockers

    api = _make_api_mock()

    def fake_rest_get(url, params=None):
        if url.endswith("/telephony/config/numbers"):
            return {
                "phoneNumbers": [
                    {"phoneNumber": "+15551234567"},
                    {"extension": "77", "owner": {"type": "VOICE_MESSAGING"}},
                ]
            }
        if url.endswith("/voicePortal"):
            return {"id": "vp1", "name": "VM-HQ"}
        return {}

    api.session.rest_get.side_effect = fake_rest_get
    blockers = _location_blockers(api, "loc1", org_id=None)
    joined = " | ".join(blockers)
    assert "numbers" in joined
    assert "+15551234567" in joined
    assert "voice portal" in joined
    assert "VM-HQ / vp1" in joined
    assert "77 (voice portal)" in joined


def test_location_blockers_detect_users_with_calling_data():
    """The user probe must request callingData=true so Control Hub accepts it."""
    from wxcli.commands.cleanup import _location_blockers

    api = _make_api_mock()

    def fake_rest_get(url, params=None):
        if url.endswith("/people"):
            assert params["callingData"] == "true"
            return {
                "items": [
                    {"id": "u1", "displayName": "Preserved User", "emails": ["keep@example.com"]}
                ]
            }
        return {}

    api.session.rest_get.side_effect = fake_rest_get
    blockers = _location_blockers(api, "loc1", org_id=None)
    joined = " | ".join(blockers)
    assert "preserved users" in joined
    assert "keep@example.com" in joined
    assert "Preserved User" in joined
    assert "u1" in joined


def test_location_blockers_ignores_people_sentinel_error_rows():
    """People API sentinel error rows should not count as real users."""
    from wxcli.commands.cleanup import _location_blockers

    api = _make_api_mock()

    def fake_rest_get(url, params=None):
        if url.endswith("/people"):
            return {
                "notFoundIds": None,
                "items": [
                    {
                        "errors": {
                            "peopleListLocationId": {
                                "code": "calling_failure",
                                "reason": "No user matching the locationId in this page",
                            }
                        }
                    }
                ],
            }
        return {}

    api.session.rest_get.side_effect = fake_rest_get
    blockers = _location_blockers(api, "loc1", org_id=None)
    assert "users" not in blockers


def test_delete_location_reports_visible_blockers(monkeypatch):
    """Exhausted retries should report concrete visible blockers."""
    import wxcli.commands.cleanup as cleanup_mod
    from wxcli.commands.cleanup import delete_location

    monkeypatch.setattr(cleanup_mod.time, "sleep", lambda s: None)

    api = _make_api_mock()

    def fake_rest_get(url, params=None):
        if url.endswith("/telephony/config/numbers"):
            return {"phoneNumbers": [{"phoneNumber": "+15551234567"}]}
        if url.endswith("/voicePortal"):
            return {"id": "vp1"}
        if url.endswith("/people"):
            return {"items": [{"id": "u1"}]}
        return {}

    api.session.rest_get.side_effect = fake_rest_get
    api.session.rest_delete.side_effect = _make_webex_error(
        "409: location is being referenced", status_code=409,
    )

    result = delete_location(
        api, {"id": "loc1", "name": "HQ"}, org_id=None,
        max_attempts=2, retry_sleep=0,
    )
    assert result.success is False
    assert result.ccp_blocked is False
    assert "visible blockers:" in (result.error or "")
    assert "preserved users" in (result.error or "")
    assert "numbers" in (result.error or "")
    assert "voice portal" in (result.error or "")


def test_delete_location_reports_preserved_user_and_number_details(monkeypatch):
    """Location delete diagnostics should name preserved users and numbers."""
    import wxcli.commands.cleanup as cleanup_mod
    from wxcli.commands.cleanup import delete_location

    monkeypatch.setattr(cleanup_mod.time, "sleep", lambda s: None)

    api = _make_api_mock()

    def fake_rest_get(url, params=None):
        if url.endswith("/people"):
            return {
                "items": [
                    {
                        "id": "u-123",
                        "displayName": "Kept Agent",
                        "emails": ["agent@preserved.example"],
                    }
                ]
            }
        if url.endswith("/telephony/config/numbers"):
            return {
                "phoneNumbers": [
                    {"phoneNumber": "+15551230000"},
                    {"extension": "88", "owner": {"type": "VOICE_MESSAGING"}},
                ]
            }
        if url.endswith("/voicePortal"):
            return {"id": "vp-123", "name": "HQ Voice Portal"}
        return {}

    api.session.rest_get.side_effect = fake_rest_get
    api.session.rest_delete.side_effect = _make_webex_error(
        "409: location is being referenced", status_code=409,
    )

    result = delete_location(
        api, {"id": "loc1", "name": "HQ"}, org_id=None,
        max_attempts=2, retry_sleep=0,
    )
    assert result.success is False
    assert "agent@preserved.example" in (result.error or "")
    assert "Kept Agent" in (result.error or "")
    assert "+15551230000" in (result.error or "")
    assert "88 (voice portal)" in (result.error or "")
    assert "HQ Voice Portal / vp-123" in (result.error or "")


def test_delete_location_numbers_ccp_skip():
    """Number delete returning CCP code marks each number as skipped, not failed."""
    from wxcli.commands.cleanup import delete_location_numbers

    api = _make_api_mock()
    api.session.rest_delete.side_effect = _make_webex_error(
        '{"errors":[{"code":"ERR.V.TRM.TMN60004"}]}', status_code=400,
    )

    results = delete_location_numbers(
        api, "loc1", ["+15551234567", "+15551234568"], org_id=None,
    )
    assert len(results) == 2
    assert all(r.ccp_blocked for r in results)
    # CCP-skipped numbers count as success so cleanup exits clean.
    assert all(r.success for r in results)


def test_format_results_summary_ccp_footer():
    """CCP-blocked locations surface a dedicated footer + retry note."""
    from wxcli.commands.cleanup import DeleteResult, format_results_summary

    results = [
        DeleteResult("Locations", "loc1", "HQ", success=False,
                     error="blocked by CCP", ccp_blocked=True),
        DeleteResult("Numbers", "+15551234567", "+15551234567", success=True,
                     ccp_blocked=True),
    ]
    output = format_results_summary(results)
    assert "CCP-blocked" in output
    assert "retry in a few hours" in output
    assert "HQ" in output
    assert "idempotent" in output


# ---------------------------------------------------------------------------
# Finding #12 — delete_location_numbers 3-batch-failure abort transitions
# ---------------------------------------------------------------------------


def test_delete_location_numbers_three_consecutive_failures_aborts():
    """Issue #14 / Finding #12: after 3 consecutive failing batches the
    function STOPS iterating and marks every un-attempted number as a
    failure with ``aborted: 3 consecutive batch failures``.

    5 batches of 5 numbers = 25 numbers total. Every batch raises, so:
      - Batch 0 (nums 0-4): counter=1, 5 failures recorded.
      - Batch 1 (nums 5-9): counter=2, 5 failures recorded.
      - Batch 2 (nums 10-14): counter=3 → abort.
        Nums 15-24 marked "aborted" (not attempted).
    Total 15 with real errors + 10 aborted = 25 results. Only 3 DELETE calls.
    """
    from wxcli.commands.cleanup import delete_location_numbers

    api = _make_api_mock()
    api.session.rest_delete.side_effect = _make_webex_error(
        "500 internal error", status_code=500,
    )

    nums = [f"+1555000{i:04d}" for i in range(25)]  # 5 batches of 5
    results = delete_location_numbers(
        api, "loc1", nums, org_id=None,
    )

    assert len(results) == 25
    assert api.session.rest_delete.call_count == 3  # stopped after 3rd batch
    # First 15 numbers have real error messages ("500 internal error").
    real_errors = [r for r in results[:15] if not r.success]
    assert len(real_errors) == 15
    assert all("500" in (r.error or "") for r in real_errors)
    # Last 10 carry the abort marker and are NOT CCP-blocked.
    aborted = results[15:]
    assert len(aborted) == 10
    assert all(not r.success for r in aborted)
    assert all(
        "aborted" in (r.error or "") and "3 consecutive" in (r.error or "")
        for r in aborted
    )


def test_delete_location_numbers_counter_resets_on_success():
    """A successful batch between failures resets the consecutive-failure
    counter, so a (F, F, OK, F, F) pattern never triggers the 3-strike abort.

    5 batches: fail, fail, ok, fail, fail. After batch 3 (OK), counter=0.
    After batches 4+5 (fail), counter=2 — never hits 3 → never aborts.
    All 25 numbers are attempted (5 DELETE calls).
    """
    from wxcli.commands.cleanup import delete_location_numbers

    api = _make_api_mock()
    api.session.rest_delete.side_effect = [
        _make_webex_error("500 err", status_code=500),   # batch 0
        _make_webex_error("500 err", status_code=500),   # batch 1
        None,                                            # batch 2 OK
        _make_webex_error("500 err", status_code=500),   # batch 3
        _make_webex_error("500 err", status_code=500),   # batch 4
    ]

    nums = [f"+1555010{i:04d}" for i in range(25)]
    results = delete_location_numbers(
        api, "loc1", nums, org_id=None,
    )

    assert len(results) == 25
    # Every batch was attempted — counter never reached 3.
    assert api.session.rest_delete.call_count == 5
    # Exactly 5 successes (the one OK batch) and 20 failures (4 bad batches).
    assert sum(1 for r in results if r.success) == 5
    assert sum(1 for r in results if not r.success) == 20
    # No result carries the "aborted" marker.
    assert not any("aborted" in (r.error or "") for r in results)


def test_delete_location_numbers_ccp_skip_does_not_count_as_failure():
    """CCP-integrated errors are treated as legitimate skips — they RESET
    the consecutive-failure counter instead of incrementing it. So three
    CCP-blocked batches in a row never abort the location.
    """
    from wxcli.commands.cleanup import delete_location_numbers

    api = _make_api_mock()
    api.session.rest_delete.side_effect = _make_webex_error(
        '{"errors":[{"code":"ERR.V.TRM.TMN60004"}]}', status_code=400,
    )

    nums = [f"+1555020{i:04d}" for i in range(20)]  # 4 batches of 5
    results = delete_location_numbers(
        api, "loc1", nums, org_id=None,
    )

    assert len(results) == 20
    # Every batch attempted — counter was reset on each CCP-skip.
    assert api.session.rest_delete.call_count == 4
    # All results are CCP-blocked AND success=True (cleanup exits clean).
    assert all(r.ccp_blocked for r in results)
    assert all(r.success for r in results)
    # None carry the "aborted" marker.
    assert not any("aborted" in (r.error or "") for r in results)


# ---------------------------------------------------------------------------
# Finding #6 — per-location 90s-wait skip when disable-calling fails
# ---------------------------------------------------------------------------


def _invoke_cleanup_run(monkeypatch, loc_items: list[dict], disable_fn):
    """Drive ``cleanup_run`` with mocked dependencies and location phase,
    returning (sleeps_captured, captured_stdout, captured_stderr, delete_calls).

    Used by the Finding #6 location-cohort tests below.
    """
    import wxcli.commands.cleanup as cleanup_mod
    from typer.testing import CliRunner

    sleeps: list[int] = []
    delete_calls: list[str] = []

    # Intercept time.sleep — only capture long (>=10s) sleeps so inner
    # retry sleeps inside helper functions don't pollute the capture.
    def _fake_sleep(s):
        if s >= 10:
            sleeps.append(s)
    monkeypatch.setattr(cleanup_mod.time, "sleep", _fake_sleep)

    monkeypatch.setattr(cleanup_mod, "get_api", lambda debug=False: _make_api_mock())
    monkeypatch.setattr(cleanup_mod, "get_org_id", lambda: None)
    monkeypatch.setattr(
        cleanup_mod, "_resolve_location_ids",
        lambda api, scope, org_id, unresolved=None: None,
    )
    monkeypatch.setattr(
        cleanup_mod, "build_inventory",
        lambda *a, **kw: {"locations": loc_items},
    )
    monkeypatch.setattr(cleanup_mod, "build_number_inventory", lambda *a, **kw: {})
    monkeypatch.setattr(cleanup_mod, "disable_location_calling", disable_fn)

    def fake_delete(api, item, org_id, **kwargs):
        delete_calls.append(item["id"])
        return cleanup_mod.DeleteResult(
            "Locations", item["id"], item["id"], success=True,
        )
    monkeypatch.setattr(cleanup_mod, "delete_location", fake_delete)

    runner = CliRunner()
    result = runner.invoke(
        cleanup_mod.app,
        ["--all", "--include-locations", "--force", "--max-concurrent", "2"],
    )
    # Typer's CliRunner merges stderr into stdout unless mix_stderr=False
    # (not available in newer typer versions — just pass output twice).
    return sleeps, result.output, result.output, delete_calls


def test_location_delete_skips_wait_for_disable_failed_cohort(monkeypatch):
    """When ``disable_location_calling`` fails for some locations and
    succeeds for others, ``time.sleep(90)`` must fire exactly once and
    ONLY before the delete pass for the succeeded-cohort. The failed
    cohort proceeds to delete immediately (no wait). (Finding #6)"""
    from wxcli.commands.cleanup import DeleteResult

    def fake_disable(api, loc_id, org_id):
        ok = loc_id == "loc-ok"
        return DeleteResult(
            "Locations", loc_id, loc_id, success=ok,
            error=None if ok else "disable failed",
        )

    loc_items = [
        {"id": "loc-ok", "name": "OK Site"},
        {"id": "loc-fail", "name": "Fail Site"},
    ]
    sleeps, _stdout, _stderr, deletes = _invoke_cleanup_run(
        monkeypatch, loc_items, fake_disable,
    )

    # Exactly one 90s sleep fired (succeeded-cohort was non-empty).
    assert sleeps == [90], f"expected one 90s sleep, got {sleeps}"
    # Both locations were deleted.
    assert set(deletes) == {"loc-ok", "loc-fail"}


def test_location_delete_no_wait_when_every_disable_fails(monkeypatch):
    """When disable fails for EVERY location, the 90s wait is skipped
    entirely — the failed-cohort delete runs, the succeeded-cohort is
    empty, no sleep fires. (Finding #6)"""
    from wxcli.commands.cleanup import DeleteResult

    def fake_disable(api, loc_id, org_id):
        return DeleteResult(
            "Locations", loc_id, loc_id, success=False, error="disable failed",
        )

    loc_items = [
        {"id": "loc-a", "name": "A"},
        {"id": "loc-b", "name": "B"},
    ]
    sleeps, _stdout, _stderr, _deletes = _invoke_cleanup_run(
        monkeypatch, loc_items, fake_disable,
    )
    assert sleeps == [], (
        f"expected no 90s sleeps when every disable failed, got {sleeps}"
    )


def test_location_delete_warning_printed_for_each_failed_disable(monkeypatch):
    """A yellow-fg warning prints for each location whose disable failed,
    naming the location and noting the 90s wait is skipped. (Finding #6)"""
    from wxcli.commands.cleanup import DeleteResult

    def fake_disable(api, loc_id, org_id):
        ok = loc_id == "loc-ok"
        return DeleteResult("Locations", loc_id, loc_id, success=ok)

    loc_items = [
        {"id": "loc-ok", "name": "OK Site"},
        {"id": "loc-fail", "name": "Fail Site"},
    ]
    _sleeps, stdout, stderr, _deletes = _invoke_cleanup_run(
        monkeypatch, loc_items, fake_disable,
    )
    combined = stdout + stderr
    assert "Fail Site" in combined
    assert "telephony detach request failed" in combined
    assert "skipping 90s wait" in combined
    # The OK site does NOT appear in any "skipping 90s wait" line.
    warning_lines = [
        ln for ln in combined.splitlines() if "skipping 90s wait" in ln
    ]
    assert warning_lines, (
        f"expected at least one 'skipping 90s wait' line, got: {combined!r}"
    )
    assert all("Fail Site" in ln for ln in warning_lines)
    # Confirm no OK Site line claimed we skipped its wait.
    assert not any("OK Site" in ln for ln in warning_lines)


def test_cleanup_run_location_phase_does_not_claim_calling_disabled(monkeypatch):
    """Operator output should describe the location call as a detach attempt."""
    from wxcli.commands.cleanup import DeleteResult

    def fake_disable(api, loc_id, org_id):
        return DeleteResult("Locations", loc_id, loc_id, success=True)

    loc_items = [{"id": "loc-ok", "name": "OK Site"}]
    _sleeps, stdout, stderr, _deletes = _invoke_cleanup_run(
        monkeypatch, loc_items, fake_disable,
    )
    combined = stdout + stderr
    assert "Attempting telephony detach on locations" in combined
    assert "Telephony detach request accepted for 1/1 locations" in combined
    assert "Disabled calling on" not in combined
