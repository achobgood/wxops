"""cc-flow's hand-written authoring commands (Plan 2 Task 11).

wxcc-flow's `schema`, `template` and `connectors` become `cc-flow
show-node-template`, `show-starter-flow` and `list-connectors`, mounted onto
the generated cc-flow group as an extension (`_lazy.GROUP_EXTENSIONS`).

Every test drives the real CLI through Typer's CliRunner with the HTTP session
patched — no live call, and no direct import of a command module.
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from tools import drift_check
from wxcli.errors import WebexError
from wxcli.main import app

PROJECT = "0123456789abcdef01234567"
ORG_UUID = "11111111-1111-1111-1111-111111111111"

runner = CliRunner()


@pytest.fixture
def http(monkeypatch):
    """Patch the one HTTP read every authoring command uses.

    `routes` maps a URL suffix to a canned body (or an exception to raise);
    every call is recorded as (url, params).
    """
    calls: list[tuple[str, dict | None]] = []
    routes: dict[str, object] = {}

    def fake_rest_get(self, url, params=None, **_kw):
        calls.append((url, params))
        for suffix, body in routes.items():
            if url.endswith(suffix):
                if isinstance(body, Exception):
                    raise body
                return body
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setenv("WEBEX_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("wxcli.config.load_config", lambda *a, **k: {})
    monkeypatch.setattr("wxcli.config.get_org_id", lambda *a, **k: ORG_UUID)
    monkeypatch.setattr("wxcli.auth.WebexSession.rest_get", fake_rest_get)
    return routes, calls


def invoke(*args):
    return runner.invoke(app, ["--no-update-check", "cc-flow", *args])


QUEUE_CONTACT = {
    "activityName": "queue-contact",
    "displayName": "Queue Contact",
    "group": "action",
    "activityType": "action",
    "inputs": [
        {"name": "destination", "required": True, "type": "string"},
        {"name": "channelType", "required": True, "type": "string",
         "defaultValue": '"TELEPHONY"'},
        {"name": "priority", "required": False, "type": "integer"},
    ],
    "outputPorts": [{"condition": "error", "isErrorPath": True}],
}


def test_extensions_mount_on_cc_flow():
    result = runner.invoke(app, ["--no-update-check", "cc-flow", "--help"],
                           env={"COLUMNS": "400", "TERM": "dumb"})
    assert result.exit_code == 0, result.output
    for name in ("show-node-template", "show-starter-flow", "list-connectors"):
        assert name in result.output, name


def test_node_template_queue_contact_override(http):
    routes, calls = http
    routes["/v2/activities"] = [QUEUE_CONTACT]
    result = invoke("show-node-template", PROJECT, "queue-contact")
    assert result.exit_code == 0, result.output
    assert '"queueId"' in result.output
    assert "'destination' → 'queueId'" in result.output
    assert '"destination"' not in result.output
    # the GET goes to the CC host, under the bare-UUID org and the project
    url, params = calls[0]
    assert url == (f"https://api.wxcc-us1.cisco.com/{ORG_UUID}/project/{PROJECT}"
                   f"/v2/activities")
    assert params == {"flowType": "FLOW"}


def test_node_template_subflow_passes_flow_type(http):
    routes, calls = http
    routes["/v2/activities"] = [{**QUEUE_CONTACT, "activityName": "end-subflow"}]
    result = invoke("show-node-template", PROJECT, "end-subflow",
                    "--flow-type", "SUBFLOW")
    assert result.exit_code == 0, result.output
    assert calls[0][1] == {"flowType": "SUBFLOW"}


def test_node_template_unknown_activity_exits_1(http):
    routes, _ = http
    routes["/v2/activities"] = [QUEUE_CONTACT]
    result = invoke("show-node-template", PROJECT, "no-such-activity")
    assert result.exit_code == 1
    assert "not found" in result.output


def test_node_template_json_is_the_raw_definition(http):
    routes, _ = http
    routes["/v2/activities"] = [QUEUE_CONTACT]
    result = invoke("show-node-template", PROJECT, "queue-contact", "-o", "json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == QUEUE_CONTACT


def test_node_template_rejects_unknown_output(http):
    _routes, calls = http
    result = invoke("show-node-template", PROJECT, "queue-contact", "-o", "yaml")
    assert result.exit_code == 2
    assert "table" in result.output and "json" in result.output
    assert calls == []


def test_starter_flow_is_local(monkeypatch):
    def no_http(*_a, **_k):
        raise AssertionError("show-starter-flow made an HTTP call")

    monkeypatch.setattr("wxcli.auth.WebexSession.rest_get", no_http)
    monkeypatch.setattr("wxcli.auth.WebexSession._request", no_http)
    monkeypatch.delenv("WEBEX_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WEBEX_TOKEN", raising=False)
    result = invoke("show-starter-flow", "-o", "json")
    assert result.exit_code == 0, result.output
    flow = json.loads(result.stdout)
    assert flow["nodes"] and flow["edges"]
    assert flow["name"] == "New_Flow"


def test_starter_flow_unknown_name_exits_1():
    result = invoke("show-starter-flow", "no-such-template")
    assert result.exit_code == 1
    assert "simple-inbound" in result.output


def test_list_connectors_merges_and_dedups(http):
    # Sources measured 200 on 2026-10-19 (docs/merge/flow-store-host-map.md
    # § list-connectors sources): http-request-v2's list is the one flows can
    # use, and it held two connectors http-request's did not.
    routes, calls = http
    routes["/play-message/inputs/connector/choices"] = {"choices": [
        {"value": "tts-1", "name": "Cisco Cloud Text-to-Speech"},
        {"value": "shared-1", "name": "Shared"},
    ]}
    routes["/http-request-v2/inputs/connectorId/choices"] = {"choices": [
        {"value": "v2-only", "name": "Webex_API_ReadWrite"},
        {"value": "http-1", "name": "My API"},
    ]}
    routes["/http-request/inputs/connectorId/choices"] = {"choices": [
        {"value": "shared-1", "name": "Shared (again)"},
        {"value": "http-1", "name": "My API (again)"},
        {"value": "v1-only", "name": "Legacy API"},
    ]}
    result = invoke("list-connectors", PROJECT, "-o", "json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == [
        {"id": "tts-1", "name": "Cisco Cloud Text-to-Speech", "type": "TTS"},
        {"id": "shared-1", "name": "Shared", "type": "TTS"},
        {"id": "v2-only", "name": "Webex_API_ReadWrite", "type": "HTTP"},
        {"id": "http-1", "name": "My API", "type": "HTTP"},
        {"id": "v1-only", "name": "Legacy API", "type": "HTTP"},
    ]
    assert [u.rsplit("/v2/activities/", 1)[1] for u, _ in calls] == [
        "play-message/inputs/connector/choices",
        "http-request-v2/inputs/connectorId/choices",
        "http-request/inputs/connectorId/choices",
    ]


def test_list_connectors_tolerates_one_failing_source(http):
    routes, _ = http
    routes["/play-message/inputs/connector/choices"] = {"choices": [
        {"value": "tts-1", "name": "Cisco Cloud Text-to-Speech"}]}
    routes["/http-request-v2/inputs/connectorId/choices"] = WebexError(
        "Bad Gateway", status_code=502)
    routes["/http-request/inputs/connectorId/choices"] = {"choices": []}
    result = invoke("list-connectors", PROJECT, "-o", "json")
    assert result.exit_code == 0, result.output
    assert [c["id"] for c in json.loads(result.stdout)] == ["tts-1"]
    # the failure is named on stderr, not swallowed
    assert "http-request-v2" in result.stderr
    assert "502" in result.stderr


def test_list_connectors_empty_exits_1(http):
    routes, _ = http
    routes["/play-message/inputs/connector/choices"] = {"choices": []}
    routes["/http-request-v2/inputs/connectorId/choices"] = {"choices": []}
    routes["/http-request/inputs/connectorId/choices"] = WebexError(
        "Bad Gateway", status_code=502)
    result = invoke("list-connectors", PROJECT)
    assert result.exit_code == 1
    assert "No connectors found." in result.output


def test_registration_parser_sees_extensions():
    drift_check._MODULE_STATE = None
    drift_check._IGNORE_CACHE.clear()
    commands = drift_check.parse_extension_commands()
    assert ("cc-flow", "show-node-template") in commands
    assert ("cc-flow", "show-starter-flow") in commands
    assert ("cc-flow", "list-connectors") in commands
    assert ("converged-recordings", "download") in commands
    surface, _top = drift_check.build_cli_surface()
    assert "show-node-template" in surface["cc-flow"]
