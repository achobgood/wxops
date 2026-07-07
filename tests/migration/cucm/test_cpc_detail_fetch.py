"""Verify informational extractor fetches common phone config details."""
from unittest.mock import MagicMock, patch
import pytest
from wxcli.migration.cucm.extractors.informational import InformationalExtractor

def _mock_connection():
    conn = MagicMock()
    conn.service = MagicMock()
    return conn

def test_cpc_detail_fetch_adds_vendor_config():
    """After listing CPCs, extractor should call getCommonPhoneConfig per item."""
    conn = _mock_connection()
    conn.service.listCommonPhoneConfig.return_value = {
        "return": {"commonPhoneConfig": [
            {"name": "Standard Common Phone", "description": "Default"},
            {"name": "Custom-WiFi-Enabled", "description": "WiFi phones"},
        ]}
    }
    def mock_get(name=""):
        if name == "Standard Common Phone":
            return {"return": {"commonPhoneConfig": {
                "name": "Standard Common Phone",
                "description": "Default",
                "vendorConfig": "<vendorConfig><BluetoothMode>0</BluetoothMode></vendorConfig>",
            }}}
        elif name == "Custom-WiFi-Enabled":
            return {"return": {"commonPhoneConfig": {
                "name": "Custom-WiFi-Enabled",
                "description": "WiFi phones",
                "vendorConfig": "<vendorConfig><WifiEnable>1</WifiEnable></vendorConfig>",
            }}}
        return {"return": None}
    conn.service.getCommonPhoneConfig.side_effect = mock_get

    with patch.object(InformationalExtractor, "paginated_list") as mock_paginated:
        mock_paginated.return_value = [
            {"name": "Standard Common Phone", "description": "Default"},
            {"name": "Custom-WiFi-Enabled", "description": "WiFi phones"},
        ]
        extractor = InformationalExtractor(conn)
        result = extractor.extract()

    assert conn.service.getCommonPhoneConfig.call_count == 2
    cpcs = extractor.results.get("common_phone_config", [])
    assert len(cpcs) == 2
    assert "vendorConfig" in cpcs[0]
    assert "BluetoothMode" in cpcs[0]["vendorConfig"]
