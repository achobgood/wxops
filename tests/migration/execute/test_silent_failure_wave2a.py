"""Wave 2A of silent-failure-hardening.

Covers handler guard-clause conversions in ``handlers.py`` (Group 2 of the
spec) plus the engine fix for Issue #18 (create op must return a webex_id).

Scope = the functions and helpers listed under "Your line range" in the
Wave 2A prompt:

* helpers: ``_resolve_agents`` return-tuple reshape (Issue #15)
* handlers converted from ``return []`` to ``return skipped(...)``:
    - ``handle_route_list_create`` (missing route_group_id)
    - ``handle_route_list_configure_numbers`` (missing route list)
    - ``handle_workspace_assign_number`` (missing workspace webex_id)
    - ``handle_voicemail_group_create`` (missing location webex_id)
    - ``handle_user_configure_settings`` (missing user webex_id)
    - ``handle_user_configure_voicemail`` (missing user webex_id)
* engine.py fix #18: ``execute_single_op(require_webex_id=True)`` surfaces a
  hard FAILED when a create op comes back with no id/code.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import pytest
from aioresponses import aioresponses

from wxcli.migration.execute.engine import BASE, execute_single_op
from wxcli.migration.execute.handlers import (
    SkippedResult,
    _resolve_agents,
    handle_call_queue_create,
    handle_hunt_group_create,
    handle_route_list_configure_numbers,
    handle_route_list_create,
    handle_user_configure_settings,
    handle_user_configure_voicemail,
    handle_voicemail_group_create,
    handle_workspace_assign_number,
)


# ---------------------------------------------------------------------------
# Issue #15 — _resolve_agents returns (resolved, skipped) tuple + callers log
# ---------------------------------------------------------------------------

class TestResolveAgentsTuple:
    def test_returns_tuple_shape(self):
        data = {"agents": ["user:a", "user:b", "user:c"]}
        deps = {"user:a": "wx-a", "user:c": "wx-c"}  # b not resolved
        result = _resolve_agents(data, deps, "agents")
        assert isinstance(result, tuple)
        resolved, skipped = result
        assert resolved == [{"id": "wx-a"}, {"id": "wx-c"}]
        assert skipped == ["user:b"]

    def test_all_resolved_empty_skipped(self):
        data = {"agents": ["user:a"]}
        deps = {"user:a": "wx-a"}
        resolved, skipped = _resolve_agents(data, deps, "agents")
        assert resolved == [{"id": "wx-a"}]
        assert skipped == []

    def test_none_resolved_all_skipped(self):
        data = {"agents": ["user:a", "user:b"]}
        deps = {}
        resolved, skipped = _resolve_agents(data, deps, "agents")
        assert resolved == []
        assert skipped == ["user:a", "user:b"]

    def test_empty_agents_list(self):
        data = {"agents": []}
        resolved, skipped = _resolve_agents(data, {}, "agents")
        assert resolved == []
        assert skipped == []

    def test_hunt_group_still_creates_with_partial_members(self):
        """Per spec resolved decision #3: partial membership is allowed."""
        data = {
            "name": "Sales HG",
            "extension": "3001",
            "location_id": "location:hq",
            "agents": ["user:alice", "user:bob", "user:charlie"],
        }
        deps = {"location:hq": "wx-loc", "user:alice": "wx-a"}
        result = handle_hunt_group_create(data, deps, {})
        # Still a create call, not a SkippedResult
        assert not isinstance(result, SkippedResult)
        _, _, body = result[0]
        assert body["agents"] == [{"id": "wx-a"}]
        assert body["name"] == "Sales HG"

    def test_hunt_group_logs_warning_per_skipped_agent(self, caplog):
        data = {
            "name": "Sales HG",
            "extension": "3001",
            "location_id": "location:hq",
            "agents": ["user:alice", "user:bob", "user:charlie"],
        }
        deps = {"location:hq": "wx-loc", "user:alice": "wx-a"}
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.handlers"):
            handle_hunt_group_create(data, deps, {})
        messages = [r.getMessage() for r in caplog.records]
        assert any("user:bob" in m for m in messages), messages
        assert any("user:charlie" in m for m in messages), messages
        # Hunt group name surfaces in the warning so operators can locate it.
        assert any("Sales HG" in m for m in messages), messages

    def test_call_queue_still_creates_with_partial_members(self):
        data = {
            "name": "Support",
            "extension": "4001",
            "location_id": "location:hq",
            "agents": ["user:alice", "user:bob"],
        }
        deps = {"location:hq": "wx-loc", "user:alice": "wx-a"}
        result = handle_call_queue_create(data, deps, {})
        assert not isinstance(result, SkippedResult)
        _, _, body = result[0]
        assert body["agents"] == [{"id": "wx-a"}]

    def test_call_queue_logs_warning_per_skipped_agent(self, caplog):
        data = {
            "name": "Support",
            "extension": "4001",
            "location_id": "location:hq",
            "agents": ["user:alice", "user:bob"],
        }
        deps = {"location:hq": "wx-loc", "user:alice": "wx-a"}
        with caplog.at_level(logging.WARNING, logger="wxcli.migration.execute.handlers"):
            handle_call_queue_create(data, deps, {})
        messages = [r.getMessage() for r in caplog.records]
        assert any("user:bob" in m for m in messages), messages
        assert any("Support" in m for m in messages), messages


# ---------------------------------------------------------------------------
# handle_route_list_create — missing route group returns SkippedResult
# ---------------------------------------------------------------------------

class TestRouteListCreate:
    def test_skipped_when_route_group_missing(self):
        data = {
            "name": "RL-NY",
            "route_group_id": "route_group:rg-ny",
            "location_id": "location:ny",
        }
        deps = {"location:ny": "wx-loc"}  # no route group
        result = handle_route_list_create(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "route_group:rg-ny" in result.reason
        assert "RL-NY" in result.reason

    def test_returns_calls_when_route_group_present(self):
        data = {
            "name": "RL-NY",
            "route_group_id": "route_group:rg-ny",
            "location_id": "location:ny",
        }
        deps = {"location:ny": "wx-loc", "route_group:rg-ny": "wx-rg"}
        result = handle_route_list_create(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "/routeLists" in url
        assert body["routeGroupId"] == "wx-rg"
        assert body["locationId"] == "wx-loc"


# ---------------------------------------------------------------------------
# handle_route_list_configure_numbers — missing route list returns Skipped
# ---------------------------------------------------------------------------

class TestRouteListConfigureNumbers:
    def test_skipped_when_route_list_missing(self):
        data = {
            "canonical_id": "route_list:rl-ny",
            "numbers": ["+15551234567"],
        }
        deps = {}
        result = handle_route_list_configure_numbers(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "route_list:rl-ny" in result.reason

    def test_noop_when_no_numbers_to_configure(self):
        data = {
            "canonical_id": "route_list:rl-ny",
            "numbers": [],
        }
        deps = {"route_list:rl-ny": "wx-rl"}
        result = handle_route_list_configure_numbers(data, deps, {})
        # Route list IS resolved — the empty numbers list is a legitimate no-op
        assert result == []

    def test_returns_calls_when_route_list_and_numbers_present(self):
        data = {
            "canonical_id": "route_list:rl-ny",
            "numbers": ["+15551234567", "+15551234568"],
        }
        deps = {"route_list:rl-ny": "wx-rl"}
        result = handle_route_list_configure_numbers(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 1
        method, _url, body = result[0]
        assert method == "PUT"
        assert len(body["numbers"]) == 2


# ---------------------------------------------------------------------------
# handle_workspace_assign_number — split skip vs no-op
# ---------------------------------------------------------------------------

class TestWorkspaceAssignNumber:
    def test_skipped_when_workspace_missing(self):
        data = {"display_name": "Lobby Phone", "phone_number": "+15551234567"}
        deps = {}
        result = handle_workspace_assign_number(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "Lobby Phone" in result.reason

    def test_noop_when_no_phone_number(self):
        data = {"canonical_id": "workspace:ws-1", "display_name": "Lobby Phone"}
        deps = {"workspace:ws-1": "wx-ws"}
        result = handle_workspace_assign_number(data, deps, {})
        # Workspace resolved but no number to assign — true no-op
        assert result == []

    def test_returns_call_when_both_present(self):
        data = {
            "canonical_id": "workspace:ws-1",
            "display_name": "Lobby Phone",
            "phone_number": "+15551234567",
        }
        deps = {"workspace:ws-1": "wx-ws"}
        result = handle_workspace_assign_number(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "PUT"
        assert "wx-ws" in url
        assert body["phoneNumbers"][0]["value"] == "+15551234567"


# ---------------------------------------------------------------------------
# handle_voicemail_group_create — missing location returns Skipped
# ---------------------------------------------------------------------------

class TestVoicemailGroupCreate:
    def test_skipped_when_location_missing(self):
        data = {
            "name": "Sales VMG",
            "extension": "8001",
            "passcode": "123456",
            "location_id": "location:hq",
        }
        deps = {}
        result = handle_voicemail_group_create(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "Sales VMG" in result.reason

    def test_noop_when_no_extension(self):
        data = {
            "name": "Sales VMG",
            "passcode": "123456",
            "location_id": "location:hq",
        }
        deps = {"location:hq": "wx-loc"}
        result = handle_voicemail_group_create(data, deps, {})
        # Location resolved but no extension configured — no-op
        assert result == []

    def test_returns_call_when_location_and_extension_present(self):
        data = {
            "name": "Sales VMG",
            "extension": "8001",
            "passcode": "123456",
            "location_id": "location:hq",
        }
        deps = {"location:hq": "wx-loc"}
        result = handle_voicemail_group_create(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 1
        method, url, body = result[0]
        assert method == "POST"
        assert "wx-loc" in url
        assert body["name"] == "Sales VMG"


# ---------------------------------------------------------------------------
# handle_user_configure_settings — missing user returns Skipped
# ---------------------------------------------------------------------------

class TestUserConfigureSettings:
    def test_skipped_when_user_missing(self):
        data = {
            "canonical_id": "user:alice",
            "call_settings": {"doNotDisturb": {"enabled": True}},
        }
        deps = {}  # no user resolved
        result = handle_user_configure_settings(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "user:alice" in result.reason

    def test_noop_when_no_settings(self):
        """Empty call_settings dict when a user IS resolved is a no-op —
        the for-loop body doesn't execute and ``calls`` stays empty."""
        data = {"canonical_id": "user:alice", "call_settings": {}}
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert result == []

    def test_returns_calls_when_user_and_settings_present(self):
        data = {
            "canonical_id": "user:alice",
            "call_settings": {
                "doNotDisturb": {"enabled": True},
                "callWaiting": {"enabled": False},
            },
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_settings(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# handle_user_configure_voicemail — missing user returns Skipped
# ---------------------------------------------------------------------------

class TestUserConfigureVoicemail:
    def test_skipped_when_user_missing(self):
        data = {
            "canonical_id": "user:alice",
            "voicemail": {"enabled": True},
        }
        deps = {}
        result = handle_user_configure_voicemail(data, deps, {})
        assert isinstance(result, SkippedResult)
        assert "user:alice" in result.reason

    def test_returns_call_when_user_present(self):
        data = {
            "canonical_id": "user:alice",
            "voicemail": {"enabled": True},
        }
        deps = {"user:alice": "wx-alice"}
        result = handle_user_configure_voicemail(data, deps, {})
        assert not isinstance(result, SkippedResult)
        assert len(result) == 1
        method, url, _body = result[0]
        assert method == "PUT"
        assert "/people/wx-alice/voicemail" in url


# ---------------------------------------------------------------------------
# Issue #18 — create op with no returned id/code is FAILED, not silent OK
# ---------------------------------------------------------------------------

class TestExecuteSingleOpRequireWebexId:
    @pytest.mark.asyncio
    async def test_create_with_empty_response_body_marked_failed(self):
        """POST /devices returns 200 but body has neither 'id' nor 'code'.

        This is the silent-failure scenario for Issue #18 — without the new
        ``require_webex_id`` gate the engine would happily mark the op
        COMPLETED with webex_id=None, breaking any dependent op that needs
        the device's ID.
        """
        url = f"{BASE}/devices"
        calls = [("POST", url, {"mac": "AA:BB:CC:DD:EE:FF"})]

        with aioresponses() as m:
            # Simulate silent success: 200 OK, empty JSON object.
            m.post(url, status=200, payload={})
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                result = await execute_single_op(
                    session, "device:d1:create", calls, sem,
                    require_webex_id=True,
                )

        assert not result.success
        assert result.status == 500
        assert "no id" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_create_with_id_in_response_succeeds(self):
        url = f"{BASE}/devices"
        calls = [("POST", url, {"mac": "AA:BB:CC:DD:EE:FF"})]

        with aioresponses() as m:
            m.post(url, status=200, payload={"id": "wx-dev-123"})
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                result = await execute_single_op(
                    session, "device:d1:create", calls, sem,
                    require_webex_id=True,
                )

        assert result.success
        assert result.webex_id == "wx-dev-123"

    @pytest.mark.asyncio
    async def test_create_with_code_only_response_succeeds(self):
        """Activation-code path: POST /devices/activationCode returns
        {"code": "...", "expiryTime": "..."} with no "id" field.
        engine.py falls back to ``code`` as the webex_id, so
        require_webex_id must accept this as success."""
        url = f"{BASE}/devices/activationCode"
        calls = [("POST", url, {"model": "Cisco 9841"})]

        with aioresponses() as m:
            m.post(url, status=200, payload={"code": "ABCD1234", "expiryTime": "2026-05-01"})
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                result = await execute_single_op(
                    session, "device:d2:create", calls, sem,
                    require_webex_id=True,
                )

        assert result.success
        assert result.webex_id == "ABCD1234"

    @pytest.mark.asyncio
    async def test_non_create_op_does_not_require_webex_id(self):
        """PUTs (configure/settings ops) legitimately return 204 No Content
        with no id. They must NOT be failed by the new gate."""
        url = f"{BASE}/people/wx-alice/features/doNotDisturb"
        calls = [("PUT", url, {"enabled": True})]

        with aioresponses() as m:
            m.put(url, status=204, payload={})
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                result = await execute_single_op(
                    session, "user:alice:configure_settings", calls, sem,
                    require_webex_id=False,
                )

        assert result.success
        assert result.webex_id is None


# ---------------------------------------------------------------------------
# Finding #3 — run_batch_ops require_webex_id gate covers activation codes
# ---------------------------------------------------------------------------


class TestRunBatchOpsRequireWebexIdForActivationCode:
    """Fix #3: ``run_batch_ops`` must gate both ``create`` AND
    ``create_activation_code`` on the require_webex_id check. Convertible
    phones use the activation-code path; a malformed/empty response body
    would otherwise slip through and masquerade as success.
    """

    @pytest.mark.asyncio
    async def test_run_batch_ops_sets_require_webex_id_for_activation_code(self):
        """Single activation-code task with an empty 200 OK response body
        must produce a FAILED OpResult carrying the ``no id/code`` error.
        """
        from wxcli.migration.execute.engine import run_batch_ops

        url = f"{BASE}/devices/activationCode"
        tasks = [{
            "op": {
                "node_id": "device:convertible1:create_activation_code",
                "op_type": "create_activation_code",
                "resource_type": "device",
            },
            "calls": [("POST", url, {"model": "Cisco 8851"})],
        }]

        with aioresponses() as m:
            # Silent success: 200 OK, empty JSON object — no id, no code.
            m.post(url, status=200, payload={})
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                results = await run_batch_ops(session, tasks, sem, ctx={})

        assert len(results) == 1
        assert not results[0].success
        # Error message is shaped by execute_single_op — see Fix #18.
        assert "no id/code" in (results[0].error or "").lower()

    @pytest.mark.asyncio
    async def test_run_batch_ops_activation_code_succeeds_with_code(self):
        """Same task shape but the response carries a ``code``: must succeed
        and that code lands in webex_id (execute_single_op falls back to
        ``code`` when ``id`` is absent)."""
        from wxcli.migration.execute.engine import run_batch_ops

        url = f"{BASE}/devices/activationCode"
        tasks = [{
            "op": {
                "node_id": "device:convertible1:create_activation_code",
                "op_type": "create_activation_code",
                "resource_type": "device",
            },
            "calls": [("POST", url, {"model": "Cisco 8851"})],
        }]

        with aioresponses() as m:
            m.post(url, status=200, payload={
                "code": "ACT-ABCD1234",
                "expiryTime": "2026-05-01T00:00:00Z",
            })
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(5)
                results = await run_batch_ops(session, tasks, sem, ctx={})

        assert len(results) == 1
        assert results[0].success
        assert results[0].webex_id == "ACT-ABCD1234"
