"""Tests for DECT network execution handlers.

Covers:
  - handle_dect_network_create
  - handle_dect_base_station_create
  - handle_dect_handset_assign
"""

from __future__ import annotations

import pytest

from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_dect_network_create,
    handle_dect_base_station_create,
    handle_dect_handset_assign,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

LOC_CID = "location:Warehouse"
LOC_WID = "Y2lzY286LzEzMi8x"
NET_CID = "dect_network:Warehouse-DECT"
NET_WID = "Y2lzY286Lzk5OQ"
ORG_WID = "Y2lzY286LzAwMQ"

CTX = {"orgId": ORG_WID}

BASE_DATA = {
    "canonical_id": NET_CID,
    "network_name": "Warehouse-DECT",
    "display_name": "Warehouse DECT Network",
    "model": "DBS-210",
    "access_code": "1234",
    "location_id": LOC_CID,
    "location_canonical_id": LOC_CID,
    "base_stations": [
        {"mac": "AABBCCDDEEFF", "display_name": "BS-1"},
        {"mac": "112233445566", "display_name": "BS-2"},
    ],
    "handset_assignments": [
        {
            "user_canonical_id": "user:jsmith",
            "display_name": "John Smith",
            "line1_canonical_id": "user:jsmith",
            "line2_canonical_id": None,
        },
        {
            "user_canonical_id": "user:bjones",
            "display_name": "Bob Jones",
            "line1_canonical_id": "user:bjones",
            "line2_canonical_id": None,
        },
    ],
}


# ---------------------------------------------------------------------------
# Registry checks
# ---------------------------------------------------------------------------

class TestHandlerRegistryDect:
    def test_dect_network_create_registered(self):
        assert ("dect_network", "create") in HANDLER_REGISTRY
        assert HANDLER_REGISTRY[("dect_network", "create")] is handle_dect_network_create

    def test_dect_base_station_create_registered(self):
        assert ("dect_network", "create_base_stations") in HANDLER_REGISTRY
        assert HANDLER_REGISTRY[("dect_network", "create_base_stations")] is handle_dect_base_station_create

    def test_dect_handset_assign_registered(self):
        assert ("dect_network", "assign_handsets") in HANDLER_REGISTRY
        assert HANDLER_REGISTRY[("dect_network", "assign_handsets")] is handle_dect_handset_assign


# ---------------------------------------------------------------------------
# handle_dect_network_create
# ---------------------------------------------------------------------------

class TestHandleDectNetworkCreate:
    def _deps(self):
        return {LOC_CID: LOC_WID}

    def test_basic_create_body(self):
        calls = handle_dect_network_create(BASE_DATA, self._deps(), CTX)
        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert f"/telephony/config/locations/{LOC_WID}/dectNetworks" in url
        assert f"orgId={ORG_WID}" in url
        assert body["name"] == "Warehouse-DECT"
        assert body["displayName"] == "Warehouse DECT Network"
        assert body["model"] == "DBS-210"
        assert body["defaultAccessCodeEnabled"] is True
        assert body["defaultAccessCode"] == "1234"

    def test_no_access_code_sets_disabled(self):
        data = {**BASE_DATA, "access_code": None}
        calls = handle_dect_network_create(data, self._deps(), CTX)
        assert len(calls) == 1
        body = calls[0][2]
        assert body["defaultAccessCodeEnabled"] is False
        assert body["defaultAccessCode"] is None

    def test_missing_location_returns_empty(self):
        data = {**BASE_DATA, "location_id": None, "location_canonical_id": None}
        calls = handle_dect_network_create(data, {}, CTX)
        assert calls == []

    def test_missing_name_returns_empty(self):
        data = {**BASE_DATA, "network_name": None, "display_name": None}
        calls = handle_dect_network_create(data, self._deps(), CTX)
        assert calls == []

    def test_location_from_deps_fallback(self):
        """When location_id is absent, falls back to prefix scan of deps."""
        data = {k: v for k, v in BASE_DATA.items() if k not in ("location_id", "location_canonical_id")}
        calls = handle_dect_network_create(data, {LOC_CID: LOC_WID}, CTX)
        assert len(calls) == 1
        assert f"/telephony/config/locations/{LOC_WID}/dectNetworks" in calls[0][1]

    def test_no_org_id_in_ctx(self):
        calls = handle_dect_network_create(BASE_DATA, self._deps(), {})
        assert len(calls) == 1
        url = calls[0][1]
        assert "orgId" not in url


# ---------------------------------------------------------------------------
# handle_dect_base_station_create
# ---------------------------------------------------------------------------

class TestHandleDectBaseStationCreate:
    def _deps(self):
        return {LOC_CID: LOC_WID, NET_CID: NET_WID}

    def test_basic_base_station_body(self):
        calls = handle_dect_base_station_create(BASE_DATA, self._deps(), CTX)
        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        expected_path = (
            f"/telephony/config/locations/{LOC_WID}"
            f"/dectNetworks/{NET_WID}/baseStations"
        )
        assert expected_path in url
        assert f"orgId={ORG_WID}" in url
        assert body["baseStationMacs"] == ["AABBCCDDEEFF", "112233445566"]

    def test_missing_location_returns_empty(self):
        data = {**BASE_DATA, "location_id": None, "location_canonical_id": None}
        calls = handle_dect_base_station_create(data, {NET_CID: NET_WID}, CTX)
        assert calls == []

    def test_missing_network_webex_id_returns_empty(self):
        """If the dect_network:create op hasn't completed, network wid is absent."""
        calls = handle_dect_base_station_create(BASE_DATA, {LOC_CID: LOC_WID}, CTX)
        assert calls == []

    def test_no_base_stations_returns_empty(self):
        data = {**BASE_DATA, "base_stations": []}
        calls = handle_dect_base_station_create(data, self._deps(), CTX)
        assert calls == []

    def test_base_stations_without_mac_skipped(self):
        data = {
            **BASE_DATA,
            "base_stations": [
                {"display_name": "NoMAC"},
                {"mac": "AABBCCDDEEFF", "display_name": "WithMAC"},
            ],
        }
        calls = handle_dect_base_station_create(data, self._deps(), CTX)
        assert len(calls) == 1
        assert calls[0][2]["baseStationMacs"] == ["AABBCCDDEEFF"]


# ---------------------------------------------------------------------------
# handle_dect_handset_assign
# ---------------------------------------------------------------------------

class TestHandleDectHandsetAssign:
    def _deps(self):
        return {
            LOC_CID: LOC_WID,
            NET_CID: NET_WID,
            "user:jsmith": "person-wid-jsmith",
            "user:bjones": "person-wid-bjones",
        }

    def test_handle_dect_handset_assign_bulk(self):
        """Assigns handsets in a single batch when under 50."""
        calls = handle_dect_handset_assign(BASE_DATA, self._deps(), CTX)
        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        expected_path = (
            f"/telephony/config/locations/{LOC_WID}"
            f"/dectNetworks/{NET_WID}/handsets/bulk"
        )
        assert expected_path in url
        assert f"orgId={ORG_WID}" in url
        assert len(body["items"]) == 2
        assert body["items"][0]["line1MemberId"] == "person-wid-jsmith"
        assert body["items"][0]["customDisplayName"] == "John Smith"
        assert body["items"][1]["line1MemberId"] == "person-wid-bjones"

    def test_handle_dect_handset_assign_with_line2(self):
        """Handset with line2_canonical_id includes line2MemberId in payload."""
        vl_cid = "virtual_line:jsmith-line2"
        data = {
            **BASE_DATA,
            "handset_assignments": [
                {
                    "user_canonical_id": "user:jsmith",
                    "display_name": "John Smith",
                    "line1_canonical_id": "user:jsmith",
                    "line2_canonical_id": vl_cid,
                },
            ],
        }
        deps = {**self._deps(), vl_cid: "vl-wid-line2"}
        calls = handle_dect_handset_assign(data, deps, CTX)
        assert len(calls) == 1
        item = calls[0][2]["items"][0]
        assert item["line1MemberId"] == "person-wid-jsmith"
        assert item["line2MemberId"] == "vl-wid-line2"

    def test_handset_batching_over_50(self):
        """Large handset sets are split into batches of 50."""
        assignments = [
            {
                "user_canonical_id": f"user:u{i}",
                "display_name": f"User {i}",
                "line1_canonical_id": f"user:u{i}",
                "line2_canonical_id": None,
            }
            for i in range(75)
        ]
        data = {**BASE_DATA, "handset_assignments": assignments}
        user_deps = {f"user:u{i}": f"wid-{i}" for i in range(75)}
        deps = {LOC_CID: LOC_WID, NET_CID: NET_WID, **user_deps}
        calls = handle_dect_handset_assign(data, deps, CTX)
        assert len(calls) == 2
        assert len(calls[0][2]["items"]) == 50
        assert len(calls[1][2]["items"]) == 25

    def test_unresolved_owner_skipped(self):
        """Handsets whose owner has no Webex ID are silently omitted."""
        data = {
            **BASE_DATA,
            "handset_assignments": [
                {
                    "user_canonical_id": "user:missing",
                    "display_name": "Missing User",
                    "line1_canonical_id": "user:missing",
                    "line2_canonical_id": None,
                },
                {
                    "user_canonical_id": "user:jsmith",
                    "display_name": "John Smith",
                    "line1_canonical_id": "user:jsmith",
                    "line2_canonical_id": None,
                },
            ],
        }
        calls = handle_dect_handset_assign(data, self._deps(), CTX)
        assert len(calls) == 1
        assert len(calls[0][2]["items"]) == 1
        assert calls[0][2]["items"][0]["line1MemberId"] == "person-wid-jsmith"

    def test_all_unresolved_returns_empty(self):
        data = {
            **BASE_DATA,
            "handset_assignments": [
                {
                    "user_canonical_id": "user:nobody",
                    "display_name": "Nobody",
                    "line1_canonical_id": "user:nobody",
                    "line2_canonical_id": None,
                },
            ],
        }
        calls = handle_dect_handset_assign(data, {LOC_CID: LOC_WID, NET_CID: NET_WID}, CTX)
        assert calls == []

    def test_missing_location_returns_empty(self):
        data = {**BASE_DATA, "location_id": None, "location_canonical_id": None}
        calls = handle_dect_handset_assign(data, {NET_CID: NET_WID}, CTX)
        assert calls == []

    def test_missing_network_wid_returns_empty(self):
        calls = handle_dect_handset_assign(BASE_DATA, {LOC_CID: LOC_WID}, CTX)
        assert calls == []

    def test_line2_not_resolved_excluded_from_item(self):
        """If line2_canonical_id is set but not resolved, omit line2MemberId."""
        data = {
            **BASE_DATA,
            "handset_assignments": [
                {
                    "user_canonical_id": "user:jsmith",
                    "display_name": "John Smith",
                    "line1_canonical_id": "user:jsmith",
                    "line2_canonical_id": "virtual_line:missing",
                },
            ],
        }
        calls = handle_dect_handset_assign(data, self._deps(), CTX)
        item = calls[0][2]["items"][0]
        assert "line2MemberId" not in item
