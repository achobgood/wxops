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


from wxcli.migration.execute.handlers import handle_bulk_line_key_template_submit


class TestBulkLineKeyTemplateSubmit:
    def test_apply_template_with_locations(self):
        data = {
            "template_canonical_id": "line_key_template:tpl-1",
            "location_canonical_ids": ["location:loc-1", "location:loc-2"],
        }
        deps = {
            "line_key_template:tpl-1": "Y2lzY29zcGFyazovL3VzL1RQTA",
            "location:loc-1": "Y2lzY29zcGFyazovL3VzL0xPQzE",
            "location:loc-2": "Y2lzY29zcGFyazovL3VzL0xPQzI",
        }
        ctx = {"orgId": "org-123"}

        calls = handle_bulk_line_key_template_submit(data, deps, ctx)

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert "/telephony/config/jobs/devices/applyLineKeyTemplate" in url
        assert body["action"] == "APPLY_TEMPLATE"
        assert body["templateId"] == "Y2lzY29zcGFyazovL3VzL1RQTA"
        assert body["locationIds"] == [
            "Y2lzY29zcGFyazovL3VzL0xPQzE",
            "Y2lzY29zcGFyazovL3VzL0xPQzI",
        ]

    def test_org_wide_when_no_locations(self):
        data = {"template_canonical_id": "line_key_template:tpl-1"}
        deps = {"line_key_template:tpl-1": "Y2lzY29zcGFyazovL3VzL1RQTA"}
        ctx = {}

        calls = handle_bulk_line_key_template_submit(data, deps, ctx)

        _, _, body = calls[0]
        assert body["action"] == "APPLY_TEMPLATE"
        assert body["templateId"] == "Y2lzY29zcGFyazovL3VzL1RQTA"
        assert "locationIds" not in body

    def test_skips_unresolved_locations_silently(self):
        data = {
            "template_canonical_id": "line_key_template:tpl-1",
            "location_canonical_ids": ["location:loc-1", "location:unresolved"],
        }
        deps = {
            "line_key_template:tpl-1": "Y2lzY29zcGFyazovL3VzL1RQTA",
            "location:loc-1": "Y2lzY29zcGFyazovL3VzL0xPQzE",
        }
        calls = handle_bulk_line_key_template_submit(data, deps, {})
        _, _, body = calls[0]
        assert body["locationIds"] == ["Y2lzY29zcGFyazovL3VzL0xPQzE"]


from wxcli.migration.execute.handlers import handle_bulk_dynamic_settings_submit


class TestBulkDynamicSettingsSubmit:
    def test_location_scoped_with_tags(self):
        data = {
            "location_canonical_id": "location:loc-1",
            "tags": [
                {
                    "familyOrModelDisplayName": "Cisco 9861",
                    "tag": "%SOFTKEY_LAYOUT_PSK1%",
                    "action": "SET",
                    "value": "fnc=sd;ext=1234",
                },
                {
                    "familyOrModelDisplayName": "Cisco 9861",
                    "tag": "%SOFTKEY_LAYOUT_PSK2%",
                    "action": "CLEAR",
                },
            ],
        }
        deps = {"location:loc-1": "LOC_WID"}
        ctx = {"orgId": "org-123"}

        calls = handle_bulk_dynamic_settings_submit(data, deps, ctx)

        assert len(calls) == 1
        method, url, body = calls[0]
        assert method == "POST"
        assert "/telephony/config/jobs/devices/dynamicDeviceSettings" in url
        assert body["locationId"] == "LOC_WID"
        assert len(body["tags"]) == 2
        assert body["tags"][0]["action"] == "SET"
        assert body["tags"][1]["action"] == "CLEAR"

    def test_org_wide_uses_empty_location_string(self):
        data = {
            "location_canonical_id": "",
            "tags": [{"familyOrModelDisplayName": "Cisco 9861",
                      "tag": "%FOO%", "action": "CLEAR"}],
        }
        calls = handle_bulk_dynamic_settings_submit(data, {}, {})
        _, _, body = calls[0]
        assert body["locationId"] == ""
