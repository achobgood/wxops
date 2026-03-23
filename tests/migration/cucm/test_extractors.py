"""Tests for CUCM extractors, shared_lines, workspaces, and helpers.

Covers:
- helpers: ref_value, ref_uuid, to_list, str_to_bool
- base: ExtractionResult
- shared_lines: SharedLineDetector
- workspaces: WorkspaceClassifier
- locations: LocationExtractor
- devices: DeviceExtractor (speed dial filtering)
- routing: RoutingExtractor (CSS member ordering)
"""

import copy
from unittest.mock import MagicMock, patch

import pytest

from tests.migration.cucm.fixtures import (
    COMMON_AREA_PHONE_FIXTURE,
    CSS_FIXTURE,
    DEVICE_POOL_FIXTURE,
    END_USER_FIXTURE,
    PHONE_FIXTURE,
    PHONE_FOUR_LINES_FIXTURE,
)
from wxcli.migration.cucm.extractors.base import ExtractionResult
from wxcli.migration.cucm.extractors.helpers import (
    ref_uuid,
    ref_value,
    str_to_bool,
    to_list,
)
from wxcli.migration.cucm.extractors.shared_lines import SharedLineDetector
from wxcli.migration.cucm.extractors.workspaces import WorkspaceClassifier


# ======================================================================
# helpers.py tests
# ======================================================================


class TestRefValue:
    """ref_value: extract _value_1 from zeep reference dicts."""

    def test_dict_input(self):
        field = {"_value_1": "DP-HQ", "uuid": "{abc-123}"}
        assert ref_value(field) == "DP-HQ"

    def test_string_input(self):
        assert ref_value("plain-string") == "plain-string"

    def test_none_input(self):
        assert ref_value(None) is None

    def test_dict_missing_value_key(self):
        field = {"uuid": "{abc-123}"}
        assert ref_value(field) is None


class TestRefUuid:
    """ref_uuid: extract uuid from zeep reference dicts."""

    def test_dict_input(self):
        field = {"_value_1": "DP-HQ", "uuid": "{abc-123}"}
        assert ref_uuid(field) == "{abc-123}"

    def test_none_input(self):
        assert ref_uuid(None) is None

    def test_dict_missing_uuid_key(self):
        field = {"_value_1": "DP-HQ"}
        assert ref_uuid(field) is None


class TestToList:
    """to_list: normalize zeep list fields to Python lists."""

    def test_list_input(self):
        items = [{"name": "a"}, {"name": "b"}]
        assert to_list(items, "line") == items

    def test_single_dict_wrapped(self):
        """Single item wrapped in outer dict → list of one."""
        field = {"line": {"name": "a"}}
        result = to_list(field, "line")
        assert result == [{"name": "a"}]

    def test_none_input(self):
        assert to_list(None, "line") == []

    def test_nested_dict_with_list(self):
        """Outer dict containing a list under the key."""
        field = {"line": [{"name": "a"}, {"name": "b"}]}
        result = to_list(field, "line")
        assert result == [{"name": "a"}, {"name": "b"}]

    def test_dict_missing_key(self):
        """Outer dict that doesn't contain the expected key."""
        field = {"other_key": "value"}
        result = to_list(field, "line")
        assert result == []


class TestStrToBool:
    """str_to_bool: convert AXL string booleans."""

    def test_true(self):
        assert str_to_bool("true") is True

    def test_false(self):
        assert str_to_bool("false") is False

    def test_none(self):
        assert str_to_bool(None) is None

    def test_case_insensitive(self):
        assert str_to_bool("True") is True
        assert str_to_bool("FALSE") is False


# ======================================================================
# ExtractionResult tests
# ======================================================================


class TestExtractionResult:
    """ExtractionResult: dataclass with success_count property."""

    def test_success_count(self):
        result = ExtractionResult(extractor="test", total=10, failed=3)
        assert result.success_count == 7

    def test_defaults(self):
        result = ExtractionResult(extractor="test")
        assert result.total == 0
        assert result.failed == 0
        assert result.errors == []
        assert result.success_count == 0

    def test_errors_list(self):
        result = ExtractionResult(
            extractor="test",
            total=5,
            failed=2,
            errors=["error1", "error2"],
        )
        assert len(result.errors) == 2
        assert result.success_count == 3


# ======================================================================
# SharedLineDetector tests
# ======================================================================


class TestSharedLineDetection:
    """SharedLineDetector: detect DNs appearing on 2+ devices."""

    def test_shared_line_detection(self):
        """Two phones sharing DN 1050 in partition Internal-PT."""
        phone_a = copy.deepcopy(PHONE_FIXTURE)
        phone_b = copy.deepcopy(PHONE_FOUR_LINES_FIXTURE)

        detector = SharedLineDetector([phone_a, phone_b])
        shared = detector.detect()

        # DN 1050 appears on both phones → one shared line record
        assert len(shared) == 1
        record = shared[0]
        assert record["dn"] == "1050"
        assert record["partition"] == "Internal-PT"
        assert record["device_count"] == 2
        assert record["canonical_id"] == "shared_line:1050:Internal-PT"

        # Primary owner: device owner with DN at line index 1.
        # Neither phone has 1050 at index 1, so primary_owner should be None.
        # (phone_a has 1050 at index 2 with owner jsmith,
        #  phone_b has 1050 at index 2 with owner jdoe)
        assert record["primary_owner"] is None

        # Both devices should be listed
        device_names = [d["device_name"] for d in record["devices"]]
        assert "SEP001122334455" in device_names
        assert "SEP112233445566" in device_names

    def test_shared_line_no_shared(self):
        """Two phones with different DNs — no shared lines."""
        phone_a = copy.deepcopy(PHONE_FIXTURE)
        # Modify phone_b so it doesn't share any DN with phone_a
        phone_b = copy.deepcopy(PHONE_FOUR_LINES_FIXTURE)
        # Remove the line with pattern 1050 from phone_b
        phone_b["lines"]["line"] = [
            line for line in phone_b["lines"]["line"]
            if line["dirn"]["pattern"] != "1050"
        ]
        # Also remove the matching line from phone_a
        phone_a["lines"]["line"] = [
            line for line in phone_a["lines"]["line"]
            if line["dirn"]["pattern"] != "1050"
        ]

        detector = SharedLineDetector([phone_a, phone_b])
        shared = detector.detect()
        assert len(shared) == 0

    def test_shared_line_speed_dial_skipped(self):
        """Line entry missing dirn (speed dial) should be skipped."""
        phone = copy.deepcopy(PHONE_FIXTURE)
        # Add a speed dial entry (no dirn key)
        phone["lines"]["line"].append({
            "index": "3",
            "label": "Speed Dial - Bob",
            "speedDialNumber": "5551234",
        })

        detector = SharedLineDetector([phone])
        # Should not crash — speed dial entries are silently skipped
        shared = detector.detect()
        # Only one phone, so no shared lines
        assert len(shared) == 0


# ======================================================================
# WorkspaceClassifier tests
# ======================================================================


class TestWorkspaceClassifier:
    """WorkspaceClassifier: identify common-area (unowned Phone-class) devices."""

    def test_workspace_classifier(self):
        """Mix of owned and unowned phones — only unowned Phone-class returned."""
        owned_phone = copy.deepcopy(PHONE_FIXTURE)  # has ownerUserName
        common_area = copy.deepcopy(COMMON_AREA_PHONE_FIXTURE)  # no owner, class=Phone

        classifier = WorkspaceClassifier([owned_phone, common_area])
        workspaces = classifier.classify()

        assert len(workspaces) == 1
        assert workspaces[0]["name"] == COMMON_AREA_PHONE_FIXTURE["name"]

    def test_workspace_classifier_cti_port_excluded(self):
        """Unowned device with class='CTI Port' should NOT be workspace."""
        cti_port = copy.deepcopy(COMMON_AREA_PHONE_FIXTURE)
        cti_port["name"] = "CTI-Lobby"
        cti_port["class"] = "CTI Port"

        classifier = WorkspaceClassifier([cti_port])
        workspaces = classifier.classify()

        assert len(workspaces) == 0


# ======================================================================
# LocationExtractor tests
# ======================================================================


class TestLocationExtractor:
    """LocationExtractor: verify AXL method calls and result aggregation."""

    def test_location_extractor_extract(self):
        """Mock AXLConnection, verify correct AXL methods called."""
        mock_conn = MagicMock()

        # paginated_list returns summary lists
        dp_summary = [{"name": "DP-HQ"}]
        dtg_summary = [{"name": "CMLocal"}]
        loc_summary = [{"name": "Hub_None"}]

        def paginated_list_side_effect(method_name, search_criteria, returned_tags, page_size=200):
            if method_name == "listDevicePool":
                return dp_summary
            elif method_name == "listDateTimeGroup":
                return dtg_summary
            elif method_name == "listLocation":
                return loc_summary
            return []

        mock_conn.paginated_list.side_effect = paginated_list_side_effect

        # get_detail returns full detail dicts
        dp_detail = copy.deepcopy(DEVICE_POOL_FIXTURE)
        dtg_detail = {"name": "CMLocal", "timeZone": "America/New_York"}

        def get_detail_side_effect(method_name, **kwargs):
            if method_name == "getDevicePool":
                return dp_detail
            elif method_name == "getDateTimeGroup":
                return dtg_detail
            return None

        mock_conn.get_detail.side_effect = get_detail_side_effect

        from wxcli.migration.cucm.extractors.locations import LocationExtractor

        extractor = LocationExtractor(mock_conn)
        result = extractor.extract()

        # Verify result counts
        assert result.extractor == "locations"
        assert result.total == 3  # 1 DP + 1 DTG + 1 location
        assert result.failed == 0
        assert result.errors == []

        # Verify stored results
        assert len(extractor.results["device_pools"]) == 1
        assert len(extractor.results["datetime_groups"]) == 1
        assert len(extractor.results["cucm_locations"]) == 1

        # Verify correct AXL methods were called
        paginated_calls = [
            call.args[0]
            for call in mock_conn.paginated_list.call_args_list
        ]
        assert "listDevicePool" in paginated_calls
        assert "listDateTimeGroup" in paginated_calls
        assert "listLocation" in paginated_calls

        get_calls = [
            call.args[0]
            for call in mock_conn.get_detail.call_args_list
        ]
        assert "getDevicePool" in get_calls
        assert "getDateTimeGroup" in get_calls


# ======================================================================
# DeviceExtractor tests
# ======================================================================


class TestDeviceExtractor:
    """DeviceExtractor: verify speed dial filtering."""

    def test_device_extractor_filters_speed_dials(self):
        """Phone with a speed dial entry (no dirn) — entry filtered out."""
        mock_conn = MagicMock()

        phone_with_speed_dial = copy.deepcopy(PHONE_FIXTURE)
        # Add a speed dial entry (no dirn)
        phone_with_speed_dial["lines"]["line"].append({
            "index": "3",
            "label": "Speed Dial - Bob",
            "speedDialNumber": "5551234",
        })

        # listPhone returns one phone summary
        mock_conn.paginated_list.return_value = [{"name": "SEP001122334455"}]

        # getPhone returns the phone with speed dial
        mock_conn.get_detail.return_value = phone_with_speed_dial

        from wxcli.migration.cucm.extractors.devices import DeviceExtractor

        extractor = DeviceExtractor(mock_conn)
        result = extractor.extract()

        assert result.total == 1
        assert result.failed == 0

        phones = extractor.results["phones"]
        assert len(phones) == 1

        # Speed dial should be filtered out — only 2 real lines remain
        lines = phones[0]["lines"]
        assert len(lines) == 2
        for line in lines:
            assert "dirn" in line


# ======================================================================
# RoutingExtractor tests
# ======================================================================


class TestRoutingExtractor:
    """RoutingExtractor: verify CSS member ordering."""

    def test_routing_extractor_css_ordering(self):
        """CSS members returned out of order should be sorted by index."""
        mock_conn = MagicMock()

        # listCss returns one CSS summary
        css_summary = [{"name": "CSS-Internal"}]
        # Other list methods return empty
        mock_conn.paginated_list.return_value = []

        def paginated_list_side_effect(method_name, search_criteria, returned_tags, page_size=200):
            if method_name == "listCss":
                return css_summary
            return []

        mock_conn.paginated_list.side_effect = paginated_list_side_effect

        # getCss returns CSS with members out of order
        css_detail = copy.deepcopy(CSS_FIXTURE)
        # Shuffle members: put index 3 first, then 1, then 2
        css_detail["members"]["member"] = [
            {
                "routePartitionName": {"_value_1": "International-PT", "uuid": "{pt-uuid-003}"},
                "index": "3",
            },
            {
                "routePartitionName": {"_value_1": "Internal-PT", "uuid": "{pt-uuid-001}"},
                "index": "1",
            },
            {
                "routePartitionName": {"_value_1": "National-PT", "uuid": "{pt-uuid-002}"},
                "index": "2",
            },
        ]

        mock_conn.get_detail.return_value = css_detail

        from wxcli.migration.cucm.extractors.routing import RoutingExtractor

        extractor = RoutingExtractor(mock_conn)
        result = extractor.extract()

        css_list = extractor.results.get("css_list", [])
        assert len(css_list) == 1

        members = css_list[0]["members"]
        assert len(members) == 3

        # Verify sorted by index: 1, 2, 3
        indices = [m["index"] for m in members]
        assert indices == ["1", "2", "3"]

        # Verify partition names match the sorted order
        partition_names = [ref_value(m["routePartitionName"]) for m in members]
        assert partition_names == ["Internal-PT", "National-PT", "International-PT"]
