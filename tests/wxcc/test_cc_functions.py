"""cc-functions and the cc-legacy-flows UI export/import (Plan 2 Task 15).

`wxcc-flow functions` (11 commands) becomes the generated `cc-functions` group
(10 commands, from the CC spec's `Functions` tag) plus the hand-written `test`
(`cc_functions_test.py`, because that operation left the spec upstream).
`cc-legacy-flows list` is renamed `export-ui` (hidden `list` alias kept) and
`import-ui` is the multipart v1 import.

Every test drives the real CLI through Typer's CliRunner with the HTTP session
patched. Nothing is sent, and no command module is imported directly.
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from wxcli.main import app

ORG_UUID = "11111111-1111-1111-1111-111111111111"
PROJECT = "0123456789abcdef01234567"
FLOW = "76543210fedcba9876543210"

runner = CliRunner()

ELEVEN = {
    "list", "show", "create", "update", "delete", "publish", "export",
    "import", "lock", "unlock", "test",
}


@pytest.fixture
def http(monkeypatch):
    """Patch every HTTP verb the commands use; record (verb, url, kwargs)."""
    calls: list[tuple[str, str, dict]] = []

    def make(verb):
        def fake(self, url, *args, **kwargs):
            calls.append((verb, url, {"args": args, **kwargs}))
            return {"ok": True}
        return fake

    monkeypatch.setenv("WEBEX_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr("wxcli.config.load_config", lambda *a, **k: {})
    monkeypatch.setattr("wxcli.config.get_org_id", lambda *a, **k: ORG_UUID)
    for verb in ("get", "post", "put", "delete", "post_multipart"):
        monkeypatch.setattr(f"wxcli.auth.WebexSession.rest_{verb}", make(verb))
    return calls


def invoke(*args, **kw):
    return runner.invoke(app, ["--no-update-check", *args],
                         env={"COLUMNS": "400", "TERM": "dumb"}, **kw)


def commands_of(group: str) -> set[str]:
    """Visible command names in a group's --help (the plain `Commands:` list)."""
    result = invoke(group, "--help")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    start = lines.index("Commands:") + 1
    return {line.split()[0] for line in lines[start:] if line.strip()}


def test_functions_group_has_eleven_commands():
    assert commands_of("cc-functions") == ELEVEN


def test_function_fields_flag_sends_fields_param(http):
    result = invoke("cc-functions", "list", "--function-fields", "id,name,status", "-o", "json")
    assert result.exit_code == 0, result.output
    verb, url, kw = http[-1]
    assert verb == "get"
    assert url.endswith(f"/v1/{ORG_UUID}/functions")
    assert kw["params"]["fields"] == "id,name,status"


def test_import_is_multipart(http, tmp_path):
    fn = tmp_path / "fn.zip"
    fn.write_bytes(b"PK-not-really-a-zip")
    result = invoke("cc-functions", "import", "--file", str(fn))
    assert result.exit_code == 0, result.output
    verb, url, kw = http[-1]
    assert verb == "post_multipart"
    assert url.endswith(f"/v1/{ORG_UUID}/functions:import")
    name, content, _ctype = kw["files"]["file"]
    assert name == "fn.zip"
    assert content == b"PK-not-really-a-zip"


def test_test_command_posts_inputs(http):
    body = {"inputs": {"a": 1, "nested": {"b": [1, 2]}}}
    result = invoke("cc-functions", "test", "fn-1", "--json-body", json.dumps(body))
    assert result.exit_code == 0, result.output
    verb, url, kw = http[-1]
    assert verb == "post"
    assert url.endswith(f"/v1/{ORG_UUID}/functions/fn-1:test")
    assert kw["json"] == body


def test_test_help_keeps_the_known_limitation_note():
    result = invoke("cc-functions", "test", "--help")
    assert result.exit_code == 0, result.output
    assert "Failed to test custom fn" in result.output
    assert "2026-07-25" in result.output


def test_delete_force_is_the_confirm_skip_flag(http):
    result = invoke("cc-functions", "delete", "fn-1", "--force", "-o", "json")
    assert result.exit_code == 0, result.output
    verb, url, kw = http[-1]
    assert verb == "delete"
    assert url.endswith(f"/v1/{ORG_UUID}/functions/fn-1")
    assert "isForceDeletion" not in (kw.get("params") or {})


def test_legacy_export_ui_and_hidden_list_alias(http):
    assert "export-ui" in commands_of("cc-legacy-flows")
    assert "list" not in commands_of("cc-legacy-flows")  # hidden alias
    for name in ("export-ui", "list"):
        http.clear()
        result = invoke("cc-legacy-flows", name, FLOW, PROJECT, "--version", "draft", "-o", "json")
        assert result.exit_code == 0, (name, result.output)
        verb, url, kw = http[-1]
        assert verb == "get"
        assert url.endswith(f"/flow-store/{ORG_UUID}/project/{PROJECT}/flows/{FLOW}:export")
        assert kw["params"] == {"version": "draft"}


def test_legacy_import_ui_is_multipart(http, tmp_path):
    ui = tmp_path / "ui.json"
    ui.write_text('{"name": "CLITest_WebexOps_x"}')
    result = invoke("cc-legacy-flows", "import-ui", PROJECT, "--file", str(ui))
    assert result.exit_code == 0, result.output
    verb, url, kw = http[-1]
    assert verb == "post_multipart"
    assert url.endswith(f"/flow-store/{ORG_UUID}/project/{PROJECT}/flows:import")
    assert kw["files"]["file"][0] == "ui.json"
