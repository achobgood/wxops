"""Tests for device settings template execution handlers."""
from wxcli.migration.execute.handlers import (
    SkippedResult,
    handle_device_settings_template_apply_location_settings,
    handle_device_settings_template_apply_device_override,
)
BASE = "https://webexapis.com/v1"


class TestApplyLocationSettings:
    def test_correct_url_and_body(self):
        data = {"location_canonical_id": "location:HQ", "settings": {"bluetooth": {"enabled": True, "mode": "PHONE"}}}
        deps = {"location:HQ": "wx-loc-abc123"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/locations/wx-loc-abc123/devices/settings" in url
        assert body["customizations"]["mpp"]["bluetooth"]["enabled"] is True
        assert body["customEnabled"] is True

    def test_with_org_id(self):
        data = {"location_canonical_id": "location:HQ", "settings": {"bluetooth": {"enabled": True}}}
        deps = {"location:HQ": "wx-loc-abc123"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {"orgId": "org-99"})
        _, url, _ = result[0]
        assert "orgId=org-99" in url

    def test_no_location_cid_returns_skipped(self):
        data = {"settings": {"bluetooth": {"enabled": True}}}
        result = handle_device_settings_template_apply_location_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "location_canonical_id" in result.reason

    def test_no_location_dep_returns_skipped(self):
        data = {"location_canonical_id": "location:HQ", "settings": {"bluetooth": {"enabled": True}}}
        result = handle_device_settings_template_apply_location_settings(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "location:HQ" in result.reason

    def test_empty_settings_returns_empty(self):
        data = {"location_canonical_id": "location:HQ", "settings": {}}
        deps = {"location:HQ": "wx-loc-abc123"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {})
        assert result == []

    def test_none_settings_returns_empty(self):
        data = {"location_canonical_id": "location:HQ", "settings": None}
        deps = {"location:HQ": "wx-loc-abc123"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {})
        assert result == []

    def test_url_contains_base(self):
        data = {"location_canonical_id": "location:HQ", "settings": {"display": {"brightness": 5}}}
        deps = {"location:HQ": "wx-loc-abc123"}
        result = handle_device_settings_template_apply_location_settings(data, deps, {})
        _, url, _ = result[0]
        assert url.startswith(BASE)


class TestApplyDeviceOverride:
    def test_correct_url_and_body(self):
        data = {"override": {"device_canonical_id": "device:SEP001122334455", "settings": {"bluetooth": {"enabled": False}}}}
        deps = {"device:SEP001122334455": "wx-dev-xyz789"}
        result = handle_device_settings_template_apply_device_override(data, deps, {})
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "/telephony/config/devices/wx-dev-xyz789/settings" in url
        assert body["customizations"]["mpp"]["bluetooth"]["enabled"] is False
        assert body["customEnabled"] is True

    def test_with_org_id(self):
        data = {"override": {"device_canonical_id": "device:SEP001", "settings": {"bluetooth": {"enabled": False}}}}
        deps = {"device:SEP001": "wx-dev-xyz789"}
        result = handle_device_settings_template_apply_device_override(data, deps, {"orgId": "org-77"})
        _, url, _ = result[0]
        assert "orgId=org-77" in url

    def test_no_override_returns_skipped(self):
        data = {}
        result = handle_device_settings_template_apply_device_override(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device_canonical_id" in result.reason

    def test_no_device_dep_returns_skipped(self):
        data = {"override": {"device_canonical_id": "device:SEPMISSING", "settings": {"bluetooth": {"enabled": False}}}}
        result = handle_device_settings_template_apply_device_override(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device:SEPMISSING" in result.reason

    def test_empty_settings_returns_empty(self):
        data = {"override": {"device_canonical_id": "device:SEP001", "settings": {}}}
        deps = {"device:SEP001": "wx-dev-xyz789"}
        result = handle_device_settings_template_apply_device_override(data, deps, {})
        assert result == []

    def test_none_override_returns_skipped(self):
        # override=None coerces to {} and device_canonical_id missing ⇒ skipped.
        data = {"override": None}
        result = handle_device_settings_template_apply_device_override(data, {}, {})
        assert isinstance(result, SkippedResult)
        assert "device_canonical_id" in result.reason

    def test_url_contains_base(self):
        data = {"override": {"device_canonical_id": "device:SEP001", "settings": {"display": {"brightness": 3}}}}
        deps = {"device:SEP001": "wx-dev-xyz789"}
        result = handle_device_settings_template_apply_device_override(data, deps, {})
        _, url, _ = result[0]
        assert url.startswith(BASE)
