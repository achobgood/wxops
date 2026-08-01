"""--verify: opt-in read-back after a write.

A 2xx proves the request was well-formed, not that the config is right —
`docs/reference/devices-core.md` records device-members accepting PRIMARY on
two ports with a 200, both persisting. --verify re-reads and reports the
fields that did not take.

Offered ONLY where a same-path GET exists. A --verify that silently verifies
nothing is worse than no flag at all: it turns an unchecked write into one that
looks checked. Every test here has a control proving the opposite case.
"""
import json

import pytest

from tools.openapi_parser import parse_tag
from tools.command_renderer import render_command_file
from wxcli.common import verify_write


def _spec(paths: dict) -> dict:
    return {"openapi": "3.0.0", "info": {"title": "t", "version": "1"}, "paths": paths}


def _op(summary: str, path_params: tuple[str, ...] = ()) -> dict:
    return {
        "tags": ["Things"],
        "summary": summary,
        "operationId": summary.replace(" ", ""),
        "parameters": [
            {"name": p, "in": "path", "required": True, "schema": {"type": "string"}}
            for p in path_params
        ],
        "responses": {"200": {"description": "ok", "content": {"application/json": {
            "schema": {"type": "object", "properties": {"id": {"type": "string"}}}}}}},
    }


def _item_op(summary: str) -> dict:
    return _op(summary, ("thingId",))


def _render(paths: dict) -> str:
    endpoints, _ = parse_tag("Things", _spec(paths), omit_query_params=["orgId"])
    return render_command_file("Things", endpoints, {})


ITEM = "/v1/things/{thingId}"


def test_put_with_a_same_path_get_offers_verify():
    code = _render({ITEM: {"get": _item_op("Get Thing"), "put": _item_op("Update Thing")}})
    assert '"--verify"' in code
    assert "verify_write(api, url," in code
    assert "from wxcli.common import verify_write" in code


def test_put_without_a_same_path_get_does_not():
    """The control. Nothing proves this endpoint's GET describes the resource."""
    code = _render({ITEM: {"put": _item_op("Update Thing")}})
    assert '"--verify"' not in code
    assert "verify_write" not in code


def test_the_import_is_omitted_when_nothing_in_the_module_can_verify():
    """Keeps 100+ untouched modules out of every regen diff."""
    code = _render({ITEM: {"get": _item_op("Get Thing")}})
    assert "from wxcli.common import verify_write" not in code


def test_a_post_is_not_offered_verify():
    """create returns the new resource already; the read-back adds nothing."""
    code = _render({"/v1/things": {"get": _op("List Things"), "post": _op("Create Thing")}})
    assert '"--verify"' not in code


def test_the_get_path_set_does_not_leak_between_modules():
    """_active_get_paths is module-global; a stale value would offer --verify
    on a module whose own spec has no read-back at all."""
    _render({ITEM: {"get": _item_op("Get Thing"), "put": _item_op("Update Thing")}})
    code = _render({ITEM: {"put": _item_op("Update Thing")}})
    assert '"--verify"' not in code


# ── runtime half: what verify_write actually reports ─────────────────────────

class _FakeSession:
    def __init__(self, result):
        self._result = result

    def rest_get(self, url, params=None):
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _FakeApi:
    def __init__(self, result):
        self.session = _FakeSession(result)


def test_verify_reports_a_field_that_did_not_take(capsys):
    api = _FakeApi({"name": "Sales", "enabled": False})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "enabled": True})
    err = capsys.readouterr().err
    assert "1 of 2 sent field(s) differ" in err
    assert "enabled: sent True, now False" in err


def test_verify_says_so_when_everything_matches(capsys):
    """Control: 'verified clean' and 'could not verify' must never look alike."""
    api = _FakeApi({"name": "Sales", "enabled": True, "serverOnly": "x"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "enabled": True})
    err = capsys.readouterr().err
    assert "all 2 sent field(s) match" in err
    assert "differ" not in err


def test_verify_ignores_fields_the_caller_did_not_send(capsys):
    """A full-response diff would flag lastModified every call and bury the signal."""
    api = _FakeApi({"name": "Sales", "lastModified": "2026-08-01T00:00:00Z"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales"})
    assert "all 1 sent field(s) match" in capsys.readouterr().err


def test_verify_flags_a_field_absent_from_the_read_back(capsys):
    api = _FakeApi({"name": "Sales"})
    verify_write(api, "/v1/queues/x", None, {"name": "Sales", "extension": "1001"})
    assert "not present in read-back" in capsys.readouterr().err


def test_a_failed_read_back_is_reported_not_swallowed(capsys):
    """Silence here would read as success — the exact failure --verify prevents."""
    api = _FakeApi(RuntimeError("403 forbidden"))
    verify_write(api, "/v1/queues/x", None, {"name": "Sales"})
    err = capsys.readouterr().err
    assert "could not re-read" in err and "403 forbidden" in err
    assert "match" not in err
