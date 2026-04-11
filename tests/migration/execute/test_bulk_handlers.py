"""Unit tests for bulk-submit handlers in execute/handlers.py."""

from __future__ import annotations

from wxcli.migration.execute.handlers import (
    HANDLER_REGISTRY,
    handle_bulk_device_settings_submit,
)


class TestBulkDeviceSettingsSubmit:
    def test_submits_post_with_location_and_customizations(self):
        data = {
            "location_canonical_id": "location:loc-1",
            "customizations": {
                "mpp": {
                    "audioCodecPriority": {
                        "primary": "OPUS",
                        "secondary": "G722",
                        "tertiary": "G711u",
                        "selection": "CUSTOM",
                    },
                    "displayNameFormat": "PERSON_FIRST_THEN_LAST_NAME",
                },
            },
        }
        deps = {"location:loc-1": "Y2lzY29zcGFyazovL3VzL0xPQw"}
        ctx = {"orgId": "org-123"}

        calls = handle_bulk_device_settings_submit(data, deps, ctx)

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert "/telephony/config/jobs/devices/callDeviceSettings" in url
        assert "orgId=org-123" in url
        assert body["locationId"] == "Y2lzY29zcGFyazovL3VzL0xPQw"
        assert body["locationCustomizationsEnabled"] is True
        assert body["customizations"]["mpp"]["displayNameFormat"] == "PERSON_FIRST_THEN_LAST_NAME"

    def test_registered_in_handler_registry(self):
        assert ("bulk_device_settings", "submit") in HANDLER_REGISTRY
        assert HANDLER_REGISTRY[("bulk_device_settings", "submit")] is handle_bulk_device_settings_submit
