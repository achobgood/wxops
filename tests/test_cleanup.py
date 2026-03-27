"""Tests for wxcli cleanup command."""
import pytest
from unittest.mock import MagicMock
import requests
from wxc_sdk.rest import RestError


def _make_rest_error(message: str = "not found") -> RestError:
    """Create a RestError with a mock response for testing."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 404
    resp.text = f'{{"message": "{message}", "errors": [], "trackingId": "test"}}'
    return RestError(message, resp)


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
    api.session.rest_delete.side_effect = _make_rest_error("not found")
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
